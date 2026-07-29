#!/usr/bin/env sh
# hook-input.sh — canonical reader for agent-hook JSON payloads.
#
# Usage: hook-input.sh <dot.path>       (stdin: the hook's JSON payload)
#   e.g. hook-input.sh .tool_input.command
#
# Prints the field's value on stdout. The two backends agree byte-for-byte on
# what hooks are meant to read: '' for null/absent (including a path through a
# non-object), 'true'/'false' for booleans, raw text for strings. Objects and
# arrays print as compact JSON under both, but *numbers are not contracted* —
# jq canonicalises number literals (jq 1.6 prints 3.0 as 3) where python3
# preserves them, bare or nested inside an object or array. Read scalar string
# or boolean fields; treat number spelling as backend-dependent.
#
# The payload must be a single JSON document. Concatenated documents
# ('{"a":"x"} {"a":"y"}') are rejected under both backends: jq would
# otherwise run the filter once per document and emit one value per line —
# 'true\nfalse' for a boolean field — where python3 rejects the payload, and
# a caller comparing the output against 'true' would read that disagreement
# as a policy answer.
#
# Exit codes: 0 read OK; 3 no working JSON parser on PATH; 4 empty or
# unparseable payload (including a multi-document one). Callers branch on the
# distinction to pick their own failure posture and message.
#
# Parses with jq, falling back to python3. *Both* backends are probed by
# running them, not by `command -v` alone: an asdf/mise shim with no version
# selected, a half-removed package or a broken wrapper resolves and then
# fails, and stock macOS ships a /usr/bin/python3 stub that passes
# `command -v` but fails until the Xcode Command Line Tools are installed.
# The jq probe runs the real filter below against '{}', not a trivial `jq .`:
# the filter needs jq >= 1.5 (try/catch, inputs), so a weaker probe would
# pass on jq 1.4 and the filter would then die on every payload. A jq that
# cannot run the filter falls through to python3; a jq that passed the probe
# and then rejects the payload is a real exit 4, not a reason to retry
# elsewhere.
#
# Consumers:
#   - Claude Code: the SessionStart probe and the PostToolUse, PreToolUse,
#     and Stop hooks in .claude/settings.json read their payloads through
#     this script.
#
# See .agents/README.md for the single-source-of-truth rationale.

payload=$(cat)
if [ -z "$payload" ]; then
	echo 'hook-input.sh: empty hook payload on stdin.' >&2
	exit 4
fi

# -n + [inputs] reads every document on stdin so the filter can insist there
# is exactly one (see header); getpath through try/catch turns a path into a
# non-object into null, matching the python3 branch.
filter='
	[inputs] as $docs
	| if ($docs | length) == 1 then $docs[0]
	  else error("not a single JSON document") end
	| ($p | split(".") | map(select(length > 0))) as $parts
	| (try getpath($parts) catch null)
	| if . == null then "" elif type == "boolean" then tostring else . end
'

if command -v jq >/dev/null 2>&1 \
	&& printf '{}' | jq -n -c -r --arg p '.probe' "$filter" >/dev/null 2>&1; then
	out=$(printf '%s' "$payload" | jq -n -c -r --arg p "$1" "$filter" 2>/dev/null) || {
		echo 'hook-input.sh: cannot parse the hook payload as a single JSON document.' >&2
		exit 4
	}
	printf '%s\n' "$out"
	exit 0
fi

if python3 -c '' >/dev/null 2>&1; then
	printf '%s' "$payload" | python3 -c '
import json, sys
try:
    v = json.load(sys.stdin)
except ValueError:
    # json.load also rejects concatenated documents ("Extra data"), so the
    # single-document contract needs no extra check on this branch.
    print("hook-input.sh: cannot parse the hook payload as a single JSON document.", file=sys.stderr)
    sys.exit(4)
for p in [p for p in sys.argv[1].split(".") if p]:
    v = v.get(p) if isinstance(v, dict) else None
if v is None:
    print("")
elif v is True or v is False:
    print(str(v).lower())
elif isinstance(v, (dict, list)):
    print(json.dumps(v, separators=(",", ":")))
else:
    print(v)
' "$1"
	exit $?
fi

echo 'hook-input.sh: no working JSON parser on PATH - jq and python3 are both missing or unable to run; cannot read the hook input. Install jq (apt-get install jq / brew install jq).' >&2
exit 3
