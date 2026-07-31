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
   `copier update`, or a partial checkout — passes `[ -r ]`, runs, and
   exits 0: every destructive command is allowed, silently. Truncation also
   has a partial shape: the guard's three rules are checked in file order, so
   a cut after the first leaves a script that still denies an unquoted
   `rm -rf` while allowing the nested-shell and SQL forms. The SessionStart
   probe (ADR 0013 Decision 4) did not cover any of it, since it exercises
   `hook-input.sh` only (issue #41).

4. **The Stop hook anchored its payload read but not the gate.** It read
   `stop_hook_active` via `"${CLAUDE_PROJECT_DIR:-.}/.agents/hooks/…"` but
   then ran a bare, cwd-dependent `make verify`. A hook cwd outside the repo
   root blocked the stop with "no makefile" — an error unrelated to the code
   (issue #44). The same applies to `just` and to a raw `verify_command`.

Alongside these, issue #40 reported that `git push --force-with-lease` — the
safe, lease-checked variant — is denied with no rephrase available, dead-ending
an agent updating a rebased branch, and named `permissions.deny`'s
`Bash(git push --force:*)` as one of the two layers denying it. Reading the
matcher (Claude Code 2.1.220) shows that half of the diagnosis is wrong: a
`:*` rule is a *whole-word* prefix, matched after collapsing runs of
whitespace as `command == prefix || command.startsWith(prefix + " ")` (plus
the same two forms behind `xargs`). `Bash(git push --force:*)` therefore never
matched `git push --force-with-lease`. The denial comes from
`block-destructive.sh`'s `operations` regex, which matches `push --force` as a
bare substring, and from `.opencode/opencode.jsonc`'s `*push --force*` glob —
both outside this ADR's scope.

## Decision

1. **Each backend is probed by running the program it will run** (amends
   ADR 0014 Decision 2's probe shape). The jq filter and the python3 script
   each live in a shell variable; the probe executes it verbatim against `{}`
   and the read executes it against the payload, so the two cannot drift
   again. A jq too old for the filter's language (`try`/`catch`, `inputs` —
   both jq 1.5) now falls through to python3 exactly as a broken jq does, and
   a python3 that starts but cannot compile or run the script (stripped
   stdlib, a python2 shim) is caught before it half-runs. The reader's exit
   codes stay 0/3/4 for callers that branch on them: a backend that passes
   its probe and then dies is a 3 naming itself, not a 1 leaking out or a 4
   blaming the payload. The exit-3 message says jq may be *missing, unable to
   run, or too old*, and asks for an install **or upgrade** — on a jq-1.4 host
   the old wording asked for an install the user had already done. ADR 0014's
   line survives intact: a backend that passed the probe and then rejects the
   payload is still a genuine exit 4.

2. **The payload must be a single JSON document** (narrows ADR 0014
   Decision 1's contract). The filter reads all documents via `-n` +
   `[inputs]` and errors unless there is exactly one, so concatenated
   documents are exit 4 under jq just as they already were under python3
   (`json.load` rejects them as "Extra data" — no change needed there).
   A whitespace-only payload, which jq previously read as zero documents
   and exited 0 on, is likewise exit 4 under both. Callers keep reading
   one value or a clean failure, never `true\nfalse`.

3. **SessionStart self-tests the guard** (extends ADR 0013 Decision 4's
   warn-early posture to `block-destructive.sh`). A hook pipes **one command
   per deny-list rule** — an unquoted operation, an operation handed to a
   nested shell, the SQL text pattern — through the guard and expects the
   deny verdict for each; anything else warns with non-blocking exit 1,
   naming the probe that failed, the guard's own stderr, the consequence and
   the remedy. One probe would not do: the rules are checked in file order,
   so a guard truncated below the first still passes it. The verdict is
   **exit 2 plus the guard's own `block-destructive: denied` stderr
   message**, not the exit code alone: dash also exits 2 when it cannot open
   or parse a script, and the deny message exists precisely to make a deny
   distinguishable from an infrastructure failure (ADR 0013 Decision 3).
   That pins the guard's message prefix as a cross-file contract; it is
   recorded beside the self-test, and the matching note in
   `block-destructive.sh`'s own header rides with the issue-#43/#45/#46 doc
   pass that owns that file. The warning distinguishes the two failure
   directions,
   which point opposite ways: PreToolUse *ends* on the guard, so a guard
   exiting 2 without a deny message denies **every** Bash call, while any
   other exit denies **none**. A missing guard keeps its own message
   (PreToolUse will deny everything — fail closed). PreToolUse's `[ -r ]`
   check is unchanged: it is still the right *blocking* posture for a missing
   file, and the self-test covers the damaged case it cannot see.

4. **The Stop gate runs from the repo root**: `cd "${CLAUDE_PROJECT_DIR:-.}"`
   precedes the gate in both the bootstrap and plain variants. `make`, `just`
   and a raw `verify_command` all resolve their task file against the cwd, so
   the anchor is runner-independent rather than a make-only `-C`. It is its
   own statement, not `cd … && <verify>`: chained, a failed `cd` would fall
   into the gate's `|| …` tail and be reported as a red gate that never ran,
   and a compound `verify_command` would run everything past its first `;`
   unanchored. A `cd` that fails (the project directory vanished mid-session)
   reports and exits 1 — like the reader failures, it is a host condition
   that would recur at every stop, so blocking on it buys nothing.

5. **`permissions.deny` keeps `Bash(git push --force:*)`**, with the
   whole-word prefix semantics recorded in a comment beside it. Issue #40's
   settings-side item is a no-op: the rule already denies `git push --force`
   and `git push --force <args>` without touching `--force-with-lease`.
   Writing the space into the rule (`Bash(git push --force :*)`) would make
   the prefix end in a space, so it would need a second space to match and
   would deny nothing — an under-deny in the one configuration where this
   list is the only layer (`include_claude_hooks=false`). The comment exists
   to keep the next reader of issue #40 from making exactly that change.

## Consequences

- On a jq 1.4 host with python3, all hooks work via the fallback; with
  neither backend usable, the reader exits 3 and both the SessionStart
  warning and the PreToolUse denial finally print the remedy that matches
  the cause. The SessionStart warning quotes the reader's own line rather
  than restating a guess at the cause.
- Multi-document and whitespace-only payloads are a uniform exit 4 under
  both backends; the Stop loop guard can no longer be defeated by a
  concatenated payload.
- Both backends now emit through command substitution, so a value carrying
  trailing newlines reads identically under either — the byte-for-byte
  contract holds where it previously diverged by one newline.
- A damaged or weakened guard surfaces as a session-start warning instead
  of a silent allow-everything; a missing one warns at session start *and*
  still fails closed at first Bash use. The Stop hook's exit-code contract
  is unchanged (2 blocks; 1 reports without blocking) — the self-test and
  the unreachable-project-directory case add exit-1 warning paths.
- The self-test embeds three deny-list literals (an `rm -rf`, the same
  inside a nested shell, and a `DROP TABLE`) in `.claude/settings.json`.
  That is settings content, not a Bash command line, so the PreToolUse guard
  never evaluates it; tooling that greps rendered output for destructive
  strings will see them.
- Until that note lands, the prefix contract is recorded on one side only:
  rewording `block-destructive.sh`'s `deny()` would start every session with
  a "guard damaged" warning and nothing on the guard side to explain why.
- `.agents/README.md`'s claim that the guard "fails closed" when damaged
  remains false in the window before the self-test's warning is acted on;
  the README correction is tracked with the issue-#43/#45/#46 doc rewrite,
  not here.
- Issue #40 stays open on the guard side: `block-destructive.sh` and
  `.opencode/opencode.jsonc` still deny `--force-with-lease` by substring,
  and nothing here changes that.
