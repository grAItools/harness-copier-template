# 16. Filter-shape jq probe, single-document payloads, a guard self-test, and an anchored Stop gate

## Status

Accepted (2026-07-30). Amends [ADR 0014](0014-reader-scalar-contract-and-stop-gate-posture.md)
Decisions 1 and 2 and extends [ADR 0013](0013-hook-payload-parsing-and-failure-postures.md)
Decision 4; prompted by issues #40, #41 and #44.

## Context

Four defects in the hook wiring as of `main` after ADR 0014's fixes landed:

1. **The jq probe proved less than the branch it gated.** ADR 0014 Decision 2
   probes jq with `printf '{}' | jq -e .` — that proves jq can *parse*, but
   the filter the reader then runs uses `try … catch`, which jq only gained
   in 1.5. On a jq 1.4 host the probe passes, the filter dies on a syntax
   error, `2>/dev/null` eats the diagnostic, and every read exits 4 — which
   PreToolUse maps to a denial of **every** Bash call, blaming the payload,
   while a working `python3` sits unused on the same PATH (issue #41). This
   is the exact failure shape ADR 0014 fixed for a *broken* jq, recurring one
   level up: the probe and the thing it vouches for had drifted apart.

2. **Concatenated JSON documents split the backends.** jq runs its filter
   once per input document and exits 0, emitting one value per line; python3
   rejects the payload. On the Stop hook the jq path could return
   `true\nfalse` for `.stop_hook_active`, which fails the `[ "$flag" =
   'true' ]` test and defeats the loop guard that flag exists for
   (issue #44). The reader's header promised backend-identical output while
   the backends disagreed about whether the payload was even readable.

3. **The PreToolUse health check proved readability, not runnability.**
   `[ -r "$H/block-destructive.sh" ] || exit 2` fails closed for a *missing*
   guard, but a present-and-damaged one — truncated by an interrupted
   `copier update`, a partial checkout, a Windows checkout without
   `core.symlinks=true` — passes `[ -r ]`, runs, and exits 0: every
   destructive command is allowed, silently. The SessionStart probe
   (ADR 0013 Decision 4) did not cover it, since it exercises
   `hook-input.sh` only (issue #41).

4. **The Stop hook anchored its payload read but not the gate.** It read
   `stop_hook_active` via `"${CLAUDE_PROJECT_DIR:-.}/.agents/hooks/…"` but
   then ran a bare, cwd-dependent `make verify`. A hook cwd outside the repo
   root blocked the stop with "no makefile" — an error unrelated to the code
   (issue #44). The same applies to `just` and to a raw `verify_command`.

Alongside these, `permissions.deny`'s `Bash(git push --force:*)` is a plain
string-prefix rule, so it also denied the safe, lease-checked
`git push --force-with-lease` — double-denying it next to the guard's own
`push --force` substring match (issue #40), with no rephrase available: an
agent updating a rebased branch was dead-ended.

## Decision

1. **The jq probe runs the real filter** (amends ADR 0014 Decision 2's probe
   shape). The filter lives in a shell variable; the probe executes it
   verbatim against `{}` and the read executes it against the payload, so
   the two cannot drift again. A jq too old for the filter's language
   (`try`/`catch`, `inputs` — both jq 1.5) now falls through to python3
   exactly as a broken jq does; on a host with such a jq and *no* python3
   the reader exits 3, whose message names the actual remedy (install a
   current jq) instead of misdiagnosing every payload. ADR 0014's line
   survives intact: a jq that passed the probe and then rejects the payload
   is still a genuine exit 4.

2. **The payload must be a single JSON document** (narrows ADR 0014
   Decision 1's contract). The filter reads all documents via `-n` +
   `[inputs]` and errors unless there is exactly one, so concatenated
   documents are exit 4 under jq just as they already were under python3
   (`json.load` rejects them as "Extra data" — no change needed there).
   A whitespace-only payload, which jq previously read as zero documents
   and exited 0 on, is likewise exit 4 under both. Callers keep reading
   one value or a clean failure, never `true\nfalse`.

3. **SessionStart self-tests the guard** (extends ADR 0013 Decision 4's
   warn-early posture to `block-destructive.sh`). A hook pipes a
   deny-listed command (`rm -rf /`) through the guard and expects the deny
   verdict; anything else warns with non-blocking exit 1, naming the
   consequence (destructive commands will pass) and the remedy. The verdict
   is **exit 2 plus the guard's own `block-destructive: denied` stderr
   message**, not the exit code alone: dash also exits 2 when it cannot
   open or parse a script, and the deny message exists precisely to make a
   deny distinguishable from an infrastructure failure (ADR 0013
   Decision 3). A missing guard gets its own message (PreToolUse will deny
   everything — fail closed), a present-but-damaged or silently weakened
   one gets the allow-everything warning. PreToolUse's `[ -r ]` check is
   unchanged: it is still the right *blocking* posture for a missing file,
   and the self-test covers the damaged case it cannot see.

4. **The Stop gate runs from the repo root**: `cd "${CLAUDE_PROJECT_DIR:-.}"
   && <verify>` prefixes the gate in both the bootstrap and plain variants.
   `make`, `just` and a raw `verify_command` all resolve their task file
   against the cwd, so the anchor is runner-independent rather than a
   make-only `-C`. A failing `cd` (the project directory vanished
   mid-session) blocks like a red gate; the `stop_hook_active` loop guard
   still bounds it.

5. **`permissions.deny` splits the force-push rule** into an exact
   `Bash(git push --force)` and a trailing-space prefix
   `Bash(git push --force :*)`, neither of which is a string prefix of
   `git push --force-with-lease`. The guard remains the canonical matcher;
   the deny list is the layer that still applies when
   `include_claude_hooks=false`, so it must not over-match either.

## Consequences

- On a jq 1.4 host with python3, all hooks work via the fallback; with
  neither backend usable, the reader exits 3 and both the SessionStart
  warning and the PreToolUse denial finally print the remedy that matches
  the cause.
- Multi-document and whitespace-only payloads are a uniform exit 4 under
  both backends; the Stop loop guard can no longer be defeated by a
  concatenated payload.
- A damaged or weakened guard surfaces as a session-start warning instead
  of a silent allow-everything; a missing one warns at session start *and*
  still fails closed at first Bash use. The Stop hook's exit-code contract
  is unchanged (2 blocks; 1 reports without blocking) — the self-test adds
  one more exit-1 warning path.
- The self-test embeds one deny-list literal (`rm -rf /`) in
  `.claude/settings.json`. That is settings content, not a Bash command
  line, so the PreToolUse guard never evaluates it; tooling that greps
  rendered output for destructive strings will see it.
- `.agents/README.md`'s claim that the guard "fails closed" when damaged
  remains false in the window before the self-test's warning is acted on;
  the README correction is tracked with the issue-#43/#45/#46 doc rewrite,
  not here.
- If Claude Code ever trims the trailing space from `Bash(git push --force
  :*)`, the rule degrades to the old over-matching prefix — the safe
  direction (over-deny, never under-deny).
