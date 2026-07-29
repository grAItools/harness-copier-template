# 17. The deny-list verdict moves to a python3 tokenizer

## Status

Accepted (2026-07-30). Supersedes the matching engine of
[ADR 0015](0015-deny-list-matching-outside-quotes.md) (whose three-rule
*model* — operations outside quotes, nested-shell strings, text patterns —
is kept) and retires the `grep -qE` constraint of ADR 0013 decision 3;
prompted by issue #40.

## Context

ADR 0015 implemented its rules as one `grep -qE` pass per rule: a single
regex grammar doing quote tracking, runner detection and operation matching
at once. Issue #40 measured eight command shapes that the pre-#39 substring
matcher denied and this grammar allows — each a fail-open regression in the
harness's only Bash backstop — with five distinct causes:

1. the runner rule's `[^'"]*` scan halts at a quote *nested inside* the
   runner's script, so `bash -c 'git fetch && echo "resetting" && git reset
   --hard origin/main'` passes;
2. `-c` had to be adjacent to the shell name, so `bash -euo pipefail -c` and
   `bash --norc -c` escape;
3. the outside-quotes prefix is `^`-anchored per line, which is unsound for a
   command carrying a multi-line quoted argument (a commit message): the
   continuation line starts *inside* the string, its closing quote reads as
   unmatched, and a trailing `&& rm -rf build` becomes unreachable;
4. bash's `$'…'` permits `\'` inside, desynchronising the POSIX-only quote
   model for the rest of the line;
5. the pipe rule cannot cross a second pipe segment and allows only a `sudo`
   prefix, so `| tee x | sh`, `| env sh`, `| timeout 5 sh` all pass.

Two more defects rode along: `push --force` prefix-matches the safe,
lease-checked `push --force-with-lease`, dead-ending an agent updating a
rebased branch (no rephrase recovers — quoting the flag stops it being a
command); and bracket-expression matching over bytes made the verdict
locale-dependent (`cd \xffx && rm -rf y`: allowed under `LANG=en_US.UTF-8`,
denied under `LC_ALL=C`).

Causes 2 and 5 are widenable prefix classes, but causes 1, 3 and 4 and the
locale dependence are structural: a line-oriented POSIX ERE cannot carry
quote state across lines, cannot express "the same quoting rules, one level
down", and matches bytes through locale-defined classes. ADR 0015 had
rejected "parsing the command properly" to keep `.agents/hooks/` on
dependency-free POSIX `sh` — but ADR 0013 had already made `python3` the
hooks' mandated fallback JSON parser, run-probed, so the dependency line the
rejection defended no longer exists in that form.

## Decision

1. **`block-destructive.sh` keeps its interface and moves its verdict into an
   embedded `python3` program.** The file stays a `#!/usr/bin/env sh` script
   reading stdin and exiting 0/2 with the same message contract; the deny-list
   stays in the same three shell variables at the top (now documented as
   literal `|`-separated strings, not regexes) and reaches the program via
   environment variables, so adding a pattern is still a one-line edit and
   the OpenCode mirror note is unchanged. The program is a hand-rolled
   scanner (not `shlex`, which cannot tokenize `$'…'`, raises on unterminated
   quotes, and discards the quote/operator structure the rules need): one
   pass producing (a) the text reachable without crossing a quote and (b) the
   pipeline/token structure, modelling `'…'`, `"…"` with escapes, `$'…'`,
   `$"…"`, backslash escapes and line continuations, fd-attached
   redirections, and `;`/`&&`/`||`/`&`/newline/pipe separators. Input is
   decoded with `surrogateescape`, so the verdict is byte-deterministic in
   every locale.
2. **Rule 1 runs twice: with quote state carried across lines, and once per
   line in isolation.** The joined pass closes cause 3 (the multi-line
   commit-message shape). The per-line pass is kept deliberately: an
   unpaired quote in an earlier line (a comment's apostrophe, a heredoc
   body) must not hide a bare operation on a later line. Its cost is that a
   multi-line quoted string whose lines read as commands stays a false
   positive — already documented as surviving in ADR 0015, now explained in
   the header by the per-line pass that causes it.
3. **Rule 2 becomes recursive: the string another shell will run is held to
   the same three rules.** A runner's argument (`sh … -c` with the `-c`
   anywhere among its options, `ssh`, `eval`, `su`) is re-checked at depth+1
   with quotes stripped once, the way the nested shell would see it — so
   `bash -c '… echo "resetting" && git reset --hard …'` is denied (the
   operation is reachable one level down) while `bash -c "grep 'rm -rf' ."`
   is now allowed (one level down it is a quoted mention; ADR 0015 carried
   it as a documented false positive). The pipe form crosses any number of
   segments and strips common wrapper prefixes (`sudo`, `env`, `nohup`,
   `timeout 5`, …) before testing for a shell. A third form restores the
   pre-#39 verdict on write-then-run: a command that both mentions an
   operation anywhere in its text and runs a shell on a file
   (`printf 'rm -rf x' > s.sh; sh s.sh`) is denied.
4. **A `push --force` match immediately followed by `-` is not the
   operation.** `--force-with-lease` and `--force-if-includes` are longer,
   lease-checked flags; the exception is generic (a match continued by `-`
   is a different flag) so `rm -rfv` stays denied. The OpenCode mirror gets
   the closest glob-expressible form: the `*push --force*` deny splits into
   an end-anchored `*push --force` plus a followed-by-space
   `*push --force *`, so the lease-checked flags are no longer
   prefix-matched there either. The matching `permissions.deny` entry in
   `.claude/settings.json` has the same defect and is fixed separately
   (issues #41/#44) with the equivalent exact-plus-trailing-space split.
5. **A missing or non-running `python3` fails closed, legibly**: the wrapper
   run-probes `python3 -c ''` (the hook-input.sh probe: a stub can resolve
   and then fail) and denies with the install remedy, mirroring the
   PreToolUse fail-closed posture of ADR 0013. An empty deny-list reaching
   the program (a damaged wrapper) also denies rather than silently
   allowing everything.
6. **A table-driven behaviour lock ships in this repo** at
   `tests/test_block_destructive.py` (stdlib `unittest`; `python3 -m
   unittest discover tests`): the guard has no Jinja, so the template source
   it tests is byte-identical to the rendered artifact. It lives here rather
   than in `template/` because generated repos are language-arbitrary — the
   template cannot assume a Python test runner downstream — and a downstream
   copy already exists (grAItools/devmm#4) for repos that want their own
   pin. It pins the true positives, the eight issue-#40 shapes, the
   #36-fixed mentions, and the documented surviving false positives, so a
   silent behaviour flip in either direction fails.

## Consequences

- All eight fail-open shapes deny again; every false positive fixed by #39
  stays allowed (verified case-by-case against v0.7.0 and the pre-fix main).
- `git push --force-with-lease` passes the guard; the verdict no longer
  depends on the locale.
- **`python3` becomes a hard dependency of the Bash guard.** On a host with
  neither working `python3` nor the will to install it, every Bash call is
  denied with a message naming the remedy — the same fail-closed posture the
  guard already had for an unreadable payload. Hosts running the hooks on
  `jq` alone previously never needed `python3`; they do now.
- The pure-POSIX property ADR 0015 defended is given up for the guard's
  *verdict*; the wrapper itself stays POSIX `sh`. ADR 0013 decision 3's
  `grep -o` reasoning is moot (there is no grep left in the decision path).
- Two ADR-0015 false positives are gone (nested-shell mention, the
  `'…'\''…'` idiom); its multi-line-string false positive survives by the
  per-line-pass decision above; a new documented false-positive class is a
  quoted mention alongside a shell-on-a-file in the same command (the price
  of re-denying write-then-run; recovery is splitting into two calls).
- Denies are marginally slower (~20–30 ms of interpreter start-up per Bash
  call, matching what `hook-input.sh` already costs on `jq`-less hosts).
- The header's blind-spot list is corrected: "a shell run from a file it
  wrote" was described as unchanged-in-kind while the pre-#39 form denied
  it; the same-command form is now denied again and the genuinely unchanged
  blind spot (a file written in an *earlier* tool call) is stated as such.

## Alternatives considered

- **Widening the ERE prefix classes (rules 2 and 5) and keeping `grep -qE`.**
  Fixes three of the eight shapes (`-euo pipefail -c`, `--norc -c`, the pipe
  chains); leaves the nested-quote, multi-line, `$'…'`, write-then-run and
  locale failures open, each structural to a line-oriented byte-matching
  grammar. Rejected as treating the symptom list, not the cause.
- **`shlex` for tokenization.** Rejected: POSIX-mode `shlex` mis-tokenizes
  `$'…'` (cause 4 would survive), raises `ValueError` on any unterminated
  quote (forcing a fail-open/fail-closed guess exactly where parsing is
  hardest), and returns bare strings, discarding the quoted-vs-reachable
  distinction rule 1 is built on.
- **Failing open when `python3` is missing** (exit 0, or a non-blocking
  exit 1 warning). Rejected: ADR 0013 chose fail-closed for PreToolUse for
  the same reason it applies here — a backstop that silently stops
  backstopping is worse than a loud dependency.
