#!/usr/bin/env sh
# block-destructive.sh — canonical destructive-command matcher.
#
# Reads candidate command text on stdin; exits 2 (naming the matched pattern
# on stderr, so a deny is distinguishable from an infrastructure failure) if it
# matches a forbidden pattern, 0 otherwise. This is the single source of truth
# for the deny-list.
#
# Consumers:
#   - Claude Code: the PreToolUse(Bash) hook in .claude/settings.json pipes the
#     tool input here.
#   - OpenCode: cannot call a script, so the deny globs in
#     .opencode/opencode.jsonc restate these patterns by hand — keep in sync.
#
# See .agents/README.md for the single-source-of-truth rationale.
pattern=$(grep -oE 'rm -rf|push --force|reset --hard|DROP TABLE' | head -n1)
[ -z "$pattern" ] && exit 0
echo "block-destructive: denied - the command matches forbidden pattern '$pattern'." >&2
exit 2
