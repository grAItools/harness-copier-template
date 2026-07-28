#!/usr/bin/env sh
# block-destructive.sh — canonical destructive-command matcher.
#
# Reads candidate command text on stdin; exits 2 (with a message naming what
# matched, so a deny is distinguishable from an infrastructure failure) if the
# command *runs* a forbidden operation, 0 otherwise. This is the single source
# of truth for the deny-list.
#
# It matches text, not intent — but it does separate a pattern that is run from
# one merely mentioned inside quotes, so read-only commands that quote a
# deny-listed string (a grep pattern, `git log --grep=…`, a printf'd fixture, a
# commit message) are allowed. Three rules:
#
#   1. an operation reached without passing through a quote  -> deny
#   2. an operation anywhere, when the command hands a string
#      to another shell to run — as an argument (sh -c / ssh /
#      eval / su) or piped in as a script (… | sh) — where
#      being quoted does not make it a mention               -> deny
#   3. a text pattern anywhere, quoted or not — SQL only ever
#      appears as a quoted argument, so its mention and its
#      use are indistinguishable                             -> deny
#
# Blind spots, unchanged in kind from the earlier plain-substring form: `eval`
# of a variable, "$(…)" command substitution, aliases, encoded payloads, a
# heredoc body whose lines read as commands, a shell run from a file it wrote,
# an interpreter whose -c is not adjacent to a shell name (bash -euo … -c), and
# any language (`python -c`) doing the same work. This is a backstop against
# accidents, not a sandbox.
#
# The deny decision deliberately stays on POSIX `grep -qE`: extracting the
# matched pattern with `grep -o` would make the decision depend on a non-POSIX
# extension that also suppresses stdout on binary-classified input, silently
# failing open in both cases.
#
# Consumers:
#   - Claude Code: the PreToolUse(Bash) hook in .claude/settings.json pipes the
#     tool input here.
#   - OpenCode: cannot call a script, so the deny globs in
#     .opencode/opencode.jsonc restate these patterns by hand — as plain
#     substrings, since a glob cannot express rule 1, so OpenCode still denies
#     the quoted mentions this script allows. Keep the patterns in sync.
#
# See .agents/README.md for the single-source-of-truth rationale.

# --- deny-list (mirror any change into .opencode/opencode.jsonc) -------------
# Destructive operations: denied when run, allowed when quoted (rules 1 and 2).
operations='rm -rf|push --force|reset --hard'
# Denied anywhere in the command text, quoted or not (rule 3).
text_patterns='DROP TABLE'
# Commands that run a string rather than read one: a quoted operation handed to
# them (as an argument, or piped in as a script) is executed, not mentioned.
nested_shell='sh[[:space:]]+-[[:alnum:]]*c|(^|[^[:alnum:]_.-])(ssh|eval|su)[[:space:]]'
nested_shell="$nested_shell"'|\|[[:space:]]*(sudo[[:space:]]+)?[a-z/]*sh([[:space:]]|$)'
# -----------------------------------------------------------------------------

# Complete quoted spans, escape-aware: to the shell a backslash-escaped quote is
# a literal character, not a delimiter, so consuming it as one would flip the
# in/out-of-quote classification for the rest of the line.
squoted="'[^']*'"                      # '…' — POSIX: no escapes inside
dquoted="\"([^\"\\\\]|\\\\.)*\""       # "…" — \" does not end the span
escaped="\\\\[\"']"                    # \" or \' outside quotes: a literal

# Characters reachable without crossing a quote: complete spans are consumed
# whole, so anything only reachable *through* a quote is a mention. Anchored per
# line — grep is line-oriented, and each line of a multi-line command starts a
# new command. A bare backslash stays an ordinary character here, so the
# alias-bypass form (\rm -rf) is still read as the operation it is.
outside_quotes="^([^'\"]|$escaped|$squoted|$dquoted)*"

cmd=$(cat)

matches() { printf '%s\n' "$cmd" | grep -qE "$1"; }

deny() {
	echo "block-destructive: denied - $1" >&2
	exit 2
}

if matches "$outside_quotes($operations)"; then
	deny "the command runs a deny-listed destructive operation.
  Deny-list: $operations.
  Only unquoted occurrences are denied, so had this been a mention inside
  quotes (a search pattern, a fixture, a commit message) it would have passed.
  This one is not quoted, so it is blocked by design."
fi

if matches "$nested_shell" && matches "$operations"; then
	deny "the command passes a deny-listed destructive operation to a nested
  shell to run — as an argument (sh -c / ssh / eval / su) or piped in as a
  script (… | sh) — where being quoted is not a mention.
  Deny-list: $operations. Blocked by design."
fi

if matches "$text_patterns"; then
	deny "the command text contains $text_patterns. This pattern is denied
  anywhere, quoted or not, because SQL only ever appears as a quoted argument,
  so a mention of it cannot be told apart from a use. To search for it, use a
  pattern that avoids the literal (e.g. DROP TABL[E])."
fi

exit 0
