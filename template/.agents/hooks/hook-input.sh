#!/usr/bin/env sh
# hook-input.sh — canonical reader for agent-hook JSON payloads.
#
# Usage: hook-input.sh <dot.path>       (stdin: the hook's JSON payload)
#   e.g. hook-input.sh .tool_input.command
#
# Prints the field's value on stdout: '' for null/absent, 'true'/'false' for
# booleans. Parses with jq when available, falling back to python3; exits 3
# (with a message) when neither is on PATH, so callers can distinguish
# "cannot read the input" from "field is empty" and pick their own failure
# posture.
#
# Consumers:
#   - Claude Code: the PostToolUse, PreToolUse, and Stop hooks in
#     .claude/settings.json read their payloads through this script.
#
# See .agents/README.md for the single-source-of-truth rationale.

if command -v jq >/dev/null 2>&1; then
	exec jq -r "$1 // empty"
fi
if command -v python3 >/dev/null 2>&1; then
	exec python3 -c '
import json, sys
v = json.load(sys.stdin)
for p in [p for p in sys.argv[1].split(".") if p]:
    v = v.get(p) if isinstance(v, dict) else None
if v is None:
    print("")
elif v is True or v is False:
    print(str(v).lower())
else:
    print(v)
' "$1"
fi
echo 'hook-input.sh: neither jq nor python3 is on PATH; cannot read the hook input. Install jq (apt-get install jq / brew install jq).' >&2
exit 3
