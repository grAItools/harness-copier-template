# 15. Deny-list matching outside quoted spans, with a nested-shell fallback

## Status

Accepted (2026-07-28). Refines ADR 0004 (canonical agent hooks) and ADR 0013
decision 3 (the deny message); prompted by issue #36. Independent of ADR 0014,
which amends the same ADR's decisions 1–2 for the payload reader. The
`grep -qE` matching engine is superseded by
[ADR 0017](0017-deny-list-tokenizer-in-python3.md) (issue #40); the
three-rule model itself is kept.

## Context

`block-destructive.sh` matched its four patterns as plain substrings of the
whole Bash tool input. ADR 0004 recorded the resulting false positives as
accepted ("a future follow-up could extract just the command before matching"),
and ADR 0013 then gave the deny an explanatory message. Adoption in a
downstream repo showed the two compounding: read-only commands that merely
*mention* a pattern — `grep -rn '<pattern>' .`, `git log --grep=…`, a `printf`
of a fixture, a commit message describing the guard — are denied with a message
asserting the command is destructive, which reads as unrecoverable. It was
observed four times in one session; the issue reporting it could not be filed
through the agent's own Bash tool, because its body quotes the deny-list.

The issue proposed anchoring the match to command position (start-of-string or
after `;`, `&`, `|`, `&&`, `||`). Measured against a suite of true positives,
that shape removes the guard rather than sharpening it: **26 of 35 destructive
samples escape it**. Three of the four patterns never appear in command
position — `push --force` and `reset --hard` follow `git` (and any global flag,
as in `git -C /repo push --force`), and `DROP TABLE` is by nature a quoted
argument to a SQL client. Even `rm -rf`, the one genuine command, is commonly
reached through a wrapper (`sudo`, `xargs`, `find -exec`). Command position is
the wrong axis: the false positives are not *mid-command* patterns, they are
*quoted* ones.

Quoting is a usable axis, with one inversion: for a shell operation, being
inside quotes means it is data (a search pattern, a fixture); for SQL, being
inside quotes is how it is *executed*. And for `sh -c` / `ssh` / `eval`, the
quotes hold a command, so the inversion applies there too.

## Decision

Keep one `grep -qE` per rule (no `grep -o`, per ADR 0013 decision 3) and split
the deny-list along the axis that actually separates use from mention:

1. **Operations** (`rm -rf`, `push --force`, `reset --hard`) are denied only
   where they are reachable **without crossing a quote**. The prefix
   `^([^'"]|\\["']|'[^']*'|"([^"\\]|\\.)*")*` consumes complete `'…'` and `"…"`
   spans, so a pattern only reachable *through* a quote is a mention and passes.
   It is escape-aware, because to the shell a backslash-escaped quote is a
   literal character, not a delimiter: reading `\"` as one would flip the
   in/out-of-quote classification for the rest of the line, both letting
   `git commit -m "8\" display" && git push --force` through and denying
   `git commit -m "see \"rm -rf\" docs"` with a message asserting it was
   unquoted. Outside quotes only an escaped *quote* is consumed as a unit, so a
   bare backslash stays an ordinary character and the alias-bypass form
   `\rm -rf` is still read as the operation it is. Matching stays line-anchored:
   `grep` is line-oriented, and each line of a multi-line command starts a new
   command.
2. **Nested-shell fallback**, scoped to the string the shell will actually run:
   past the quote a runner opens (`sh -c`, `ssh`, `eval`, `su`) with no command
   separator in between, or ahead of a pipe into a shell. Being quoted is not a
   mention there. Two boundaries matter, and both were found by review of the
   looser first draft:
   - Shell names are **listed** (`sh|bash|dash|zsh|ksh|ash`), never matched as
     an `sh` suffix — `push` and `refresh` end in `sh`, so a suffix match denied
     `git push -c k=v && grep '<pattern>' .`.
   - The runner and the operation must be **related**, not merely co-resident on
     the line. A plain conjunction ("a runner appears" AND "an operation
     appears") denied `ssh host uptime && grep '<pattern>' .`. `ssh`, `eval` and
     `su` are also absent from the piped form: they run an argument, not stdin,
     so `grep '<pattern>' . | ssh host tee f` is a mention.
   Unquoted forms need no help from this rule — `ssh host rm -rf /tmp/x` is
   already reachable without crossing a quote, so rule 1 denies it.
3. **Text patterns** (`DROP TABLE`) stay matched anywhere, quoted or not. SQL
   has no unquoted form to anchor to, so a mention is genuinely
   indistinguishable from a use; the deny message says so and shows how to
   search for the literal.
4. **The message describes the mechanism, not the intent** (extending ADR 0013
   decision 3): each rule states what matched and why *that* is the rule, so a
   surviving false positive reads as a one-turn rephrase rather than a verdict
   on the task.

The deny-list stays in three named shell variables at the top of the script,
so adding a pattern is still a one-line edit that picks a rule.

## Consequences

- Every false positive reported in the issue passes: grepping for the deny-list
  (including this repo's own harness), `git log --grep`, `printf` of a fixture,
  a commit message that names a pattern. A 61-assertion suite pins them
  alongside the true positives; the previous matcher fails 20 of them.
- No true positive lost among the plain and chained forms: `cd x && rm -rf y`,
  `sudo rm -rf`, `\rm -rf`, `find -exec rm -rf`, `xargs rm -rf`,
  `git -C … push --force`, a quoted commit message followed by a real operation
  (with or without escaped quotes inside it), unquoted `$(…)` and backtick
  substitution, `sh -c "…"` (including `sh -c 'cd x && rm -rf y'`, whose
  separator sits inside the runner's argument), `ssh host '…'`,
  `ssh host rm -rf …`, `xargs -I{} sh -c "…"`, `sudo -u x sh -c "…"`,
  `eval "…"`, `echo '…' | sh`, and SQL in a quoted argument are all still
  denied.
- Accepted new blind spots, both in the "quoted, yet executed" class the rule-2
  list only partly covers: `"$(rm -rf x)"` (the substitution is inside a
  double-quoted span; the unquoted form is still caught), and an interpreter
  whose `-c` is not adjacent to a shell name (`bash -euo pipefail -c "…"`).
  Widening rule 2 to any `-c` flag was rejected: it would re-deny `grep -c
  '<pattern>' file`, a read-only command in the exact class being fixed. The
  other two forms found by review — an escaped quote flipping quote parity, and
  a quoted operation piped into a shell — were closed rather than accepted
  (decisions 1 and 2).
- Surviving false positives, documented in the script and in
  `development/harness-usage.md`: a quoted mention of `DROP TABLE`, a heredoc
  body or multi-line quoted string whose lines read as commands, a mention
  inside a nested-shell string (`bash -c "grep '<pattern>' ."`), and a mention
  inside the `'…'\''…'` idiom — there the empty `''` span the grammar must
  allow gives the matcher a second parse in which the pattern is reachable.
  Dropping empty spans (`'[^']+'`) would close it, but then any `''` argument
  earlier in the line would blind the matcher to a real operation after it: a
  false negative traded for a false positive, the wrong direction. Rule 1's
  message therefore states what the *matcher* reached rather than asserting the
  text was unquoted, so it stays true in these cases.
- The OpenCode mirror **diverges by design**. `permission.bash` globs cannot
  express rule 1, so OpenCode keeps `*…*` substring denies and still refuses
  quoted mentions. ADR 0004's "hand-kept mirror" rule now means *the same
  patterns*, not the same semantics; the divergence is recorded in the script
  header, `.opencode/opencode.jsonc`, and the harness-usage comparison table.
- The guard remains a backstop against accidents, not a sandbox: `eval` of a
  variable, aliases, encoded payloads and `python -c` defeat it as before. The
  script header lists these so the next reader does not mistake it for one.
- Cost: the matcher grows from one line to three rules and reads stdin into a
  variable (up to three `grep` runs per Bash call, ~8 ms on a 100 kB input;
  the quote-consuming prefix is DFA-safe and shows no backtracking blowup on
  GNU or BusyBox `grep`).

## Alternatives considered

- **Command-position anchoring, as proposed in the issue.** Rejected: 26 of 35
  true positives escape it (see Context). Trading false positives for false
  negatives in a guard is the wrong direction.
- **Softening the message only** (the issue's option 2, which would have
  resolved every observed instance). Adopted, but not on its own: it leaves
  every mention denied, so an agent working on the harness still cannot grep
  for the deny-list without a rephrase round-trip.
- **Excluding quoted spans for `DROP TABLE` too.** Rejected: it would make the
  pattern unmatchable in its only real form, `psql -c "DROP TABLE …"`.
- **An allow-list of read-only tools** (`grep`, `rg`, `printf`, `git log`)
  skipping the check. Rejected: it decides on the first word of the command, so
  `grep '<pattern>' . && rm -rf x` would pass entirely, whereas rule 1 judges
  each occurrence on its own.
- **Parsing the command properly** (a shell-grammar parser in the hook).
  Rejected: `.agents/hooks/` is POSIX `sh` with no dependencies by ADR 0004,
  and ADR 0013 kept even JSON parsing to `jq`-or-`python3`.
