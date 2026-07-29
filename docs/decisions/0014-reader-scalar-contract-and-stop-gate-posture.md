# 14. Scalar-only reader contract, run-probed backends, and a Stop gate that reports instead of skipping

## Status

Accepted (2026-07-28). Amends [ADR 0013](0013-hook-payload-parsing-and-failure-postures.md)
Decisions 1 and 2; prompted by issues #34 and #35. Decisions 1 and 2 amended
by [ADR 0016](0016-filter-shape-probe-guard-selftest-anchored-gate.md) — see
it for the single-document payload contract and the filter-shape jq probe.

## Context

Three defects in the v0.7.0 hook wiring, all surfaced by an adversarial review
of the downstream adoption in `grAItools/devmm` (devmm#4):

1. **The reader's parity contract was false for non-scalars.** `hook-input.sh`
   promised backend-identical output, but the `jq` branch called `jq -r`
   without `-c`, so objects and arrays came back pretty-printed where the
   `python3` fallback emitted `json.dumps` defaults (`{"b": 1}`) — and neither
   matched the other even after compaction, because the two use different
   separators. Numbers differ for a deeper reason: `jq` canonicalises number
   literals (jq 1.6 prints `3.0` as `3`, bare or nested) while `python3`
   preserves them. No shipped consumer is affected — the three call sites read
   `.tool_input.command`, `.tool_input.file_path` and `.stop_hook_active`, all
   strings or a boolean — but the reader exists precisely so that a hook
   behaves the same with or without `jq`, and a documented contract that is
   false invites a future author to trust it.

2. **A *broken* `jq` was worse than no `jq`.** The backend was selected on
   `command -v jq` alone, with no fall-through: any subsequent `jq` failure
   was reported as an unparseable payload (exit 4) and `python3` was never
   tried. That is the exact hazard ADR 0013 named for `python3` and guarded
   against by *running* it — and it applies to `jq` too: an asdf/mise shim
   with no version selected, a half-removed package, a wrapper script all
   resolve and then fail. Since PreToolUse maps every reader failure to
   `exit 2`, a broken `jq` denied **every** Bash call for the whole session —
   issue #31's failure mode restored on a narrower set of hosts — and the
   denial blamed the payload, so the printed remedy was not the one needed.

3. **The Stop hook skipped the gate where its predecessor ran it.** ADR 0013
   Decision 2 chose fail-open for Stop (exit 1, skip) to avoid an infinite
   loop. But the pre-0013 hook, on a host with no `jq`, got an empty
   substitution, fell through its loop guard, and **still ran the gate**: the
   loop guard was defeated (issue #31's finding 2) but enforcement survived.
   v0.7.0 traded a defeated loop guard for a skipped gate while the generated
   `AGENTS.md` / `development/harness-usage.md` kept saying "done means the
   gate is green". The postures were also asymmetric — for the identical
   condition PreToolUse failed closed (deny) and Stop failed open (skip) — so
   a parser-less host could accumulate unguarded edits and then end the
   session unverified.

## Decision

1. **The reader is contracted for scalars only** (narrows ADR 0013 Decision
   1's "output is backend-identical"). `jq -c` plus `separators=(",", ":")` on
   the `python3` side make objects and arrays byte-identical compact JSON
   under both backends; strings, booleans and null/absent (including a path
   through a non-object) already agreed. Numbers cannot be reconciled — the
   canonicalisation lives in `jq`'s number handling, not in a formatting flag
   — so the header states that outright rather than promising parity it cannot
   keep: read scalar string or boolean fields, and treat number spelling as
   backend-dependent.

2. **Both backends are probed by running them, and `jq` falls through.**
   `command -v jq >/dev/null 2>&1 && printf '{}' | jq -e . >/dev/null 2>&1`
   gates the `jq` branch; a `jq` that cannot run drops to `python3` exactly as
   a missing one does, and only when *both* fail does the reader exit 3. A
   `jq` that passed the probe and then rejects the payload is still a genuine
   exit 4: distinguishing "`jq` could not run" from "`jq` ran and rejected
   this payload" is what makes a two-backend design worth having. The
   SessionStart warning now runs the reader itself
   (`printf '{}' | sh .agents/hooks/hook-input.sh .probe`) instead of keeping
   its own `command -v jq` copy, so it cannot disagree with what the hooks
   will do — and it now fires for a broken `jq` with no `python3`, which the
   old check missed.

3. **Stop runs the gate on any reader failure, and reports rather than
   blocks** (replaces ADR 0013 Decision 2's *Stop: fail open — skip the
   gate*). The hook sets `fail=2`, downgrades it to `fail=1` when the reader
   returns non-zero, and ends with `<verify> || { … exit "$fail"; }` — where
   the `…` prints an explicit "the gate FAILED and the stop was not blocked"
   line **on stderr** in the `fail=1` case, because a gate's own failure
   output normally goes to stdout, which Claude Code does not put in front of
   the user on a non-blocking exit. Without that line the "report" would be
   invisible, which is the whole property this decision buys. The three
   options weighed in issue #35:

   - *Run the gate and keep `exit 2`* (the issue's option 1) — rejected. Its
     premise, "rely on exit 2's own loop-protection", does not hold:
     `stop_hook_active` **is** the documented protection — Claude Code's hook
     reference offers it as the way to keep a Stop hook from running
     indefinitely, with no separate cap to fall back on — and it is exactly
     what a failed read hides. The failure that
     hid it is a host condition (no parser, damaged reader), so it recurs on
     every subsequent Stop — an unbounded block/continue loop, on a host where
     the agent usually cannot run Bash to fix anything, because PreToolUse
     denies on the same failure. A wedged, token-burning session is a worse
     outcome than an unenforced gate.
   - *Fail open only for `rc=3`* (option 2) — rejected for the same reason at
     one remove: an unparseable payload or a damaged reader is just as
     persistent as a missing parser, so `exit 2` on `rc=4` loops identically.
   - *Keep as-is and soften the docs* (option 3) — rejected as the only
     measure; it accepts a silently skipped gate as the steady state.

   Taking the gate run out of the loop-risk equation keeps both properties the
   issue asks for: the gate is computed and its result surfaced (exit 1 is a
   non-blocking error, whose stderr Claude Code shows the user — hence the
   explicit stderr line above), and nothing can loop. The docs change lands with it — `development/harness-usage.md`
   now says the gate reports rather than blocks on such a host, so "done means
   the gate is green" is not silently false there.

## Consequences

- A broken `jq` now degrades to the `python3` path instead of denying every
  Bash call for the session; the remaining exit-3 denial means both backends
  are genuinely unavailable, which is what its message says.
- Objects and arrays read identically under either backend. Number-valued
  fields stay backend-dependent *by contract*; no shipped hook reads one, and
  a future hook that needs one must canonicalise it itself.
- On a reader-failure host the Stop hook runs `verify` at every stop attempt
  and never blocks: the session ends with a visible red-gate report instead of
  a silent skip. The cost is one extra gate run per stop there, and no
  enforcement — accepted, because enforcement requires a loop guard that host
  cannot supply.
- PreToolUse keeps its fail-closed posture (ADR 0013 Decision 2, otherwise
  unchanged). The asymmetry with Stop is now deliberate and much narrower:
  Stop still *runs* the gate, it just cannot block on the result.
- `.claude/settings.json` and `.agents/hooks/hook-input.sh` are template-owned,
  so `copier update` delivers all of this; downstream repos carrying local
  patches for either defect should drop them.
