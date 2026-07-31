#!/usr/bin/env sh
# hook-input.sh — canonical reader for agent-hook JSON payloads.
#
# Usage: hook-input.sh <dot.path>       (stdin: the hook's JSON payload)
#   e.g. hook-input.sh .tool_input.command
#
# Prints the field's value on stdout, followed by exactly one newline; any
# trailing newlines the value itself carries are stripped (both backends emit
# through command substitution, which drops them). The two backends agree
# byte-for-byte on what hooks are meant to read: '' for null/absent (including
# a path through a non-object), 'true'/'false' for booleans, raw text for
# strings. Objects and arrays print as compact JSON under both, but *numbers
# are not contracted* — jq canonicalises number literals (jq 1.6 prints 3.0 as
# 3) where python3 preserves them, bare or nested inside an object or array.
# Read scalar string or boolean fields; treat number spelling as
# backend-dependent.
#
# The payload must be a single JSON document. Concatenated documents
# ('{"a":"x"} {"a":"y"}') are rejected under both backends: jq would
# otherwise run the filter once per document and emit one value per line —
# 'true\nfalse' for a boolean field — where python3 rejects the payload, and
# a caller comparing the output against 'true' would read that disagreement
# as a policy answer.
#
# Exit codes: 0 read OK; 3 no usable JSON parser (missing, unable to run, or
# too old for this reader's program); 4 empty or unparseable payload
# (including a multi-document one). Nothing else is returned — a backend that
# passes its probe and then dies is a 3, not a 1 leaking to callers who only
# branch on 0/3/4. Callers use the distinction to pick their own failure
# posture and message.
#
# Parses with jq, falling back to python3. *Both* backends are probed by
# running the exact program the read will run — the filter and the python3
# script below, against '{}' — not by `command -v` and not by a stand-in like
# `jq -e .` or `python3 -c ''`: an asdf/mise shim with no version selected, a
# half-removed package or a broken wrapper resolves and then fails; stock
# macOS ships a /usr/bin/python3 stub that passes `command -v` but fails until
# the Xcode Command Line Tools are installed; and a jq older than 1.5 parses
# JSON but not the filter's language (try/catch, inputs), so a weaker probe
# would pass and the filter would then die on every payload. A backend that
# cannot run its program falls through to the next; a backend that passed the
# probe and then rejects the payload is a real exit 4, not a reason to retry
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
	out=$(printf '%s' "$payload" | jq -n -c -r --arg p "$1" "$filter" 2>/dev/null)
	rc=$?
	if [ "$rc" -eq 0 ]; then
		printf '%s\n' "$out"
		exit 0
	fi
	# jq raises 5 for an uncaught error — an unparseable payload read through
	# `inputs`, and the filter's own single-document check — and 2 for a system
	# error reading it; both are the payload's doing. Anything else is jq dying
	# after it passed the probe, which is the reader's problem to name, not the
	# payload's (the python3 branch below splits the same way).
	if [ "$rc" -eq 5 ] || [ "$rc" -eq 2 ]; then
		echo 'hook-input.sh: cannot parse the hook payload as a single JSON document.' >&2
		exit 4
	fi
	echo "hook-input.sh: jq passed its probe and then failed (exit $rc); cannot read the hook input. Repair jq (apt-get install jq / brew install jq), or install python3." >&2
	exit 3
fi

script='
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
'

# Probing with the script, not `python3 -c ''`, is what makes exit 3 true for
# a python3 that starts but cannot run it — a stripped stdlib (no json), or a
# python2 shim, whose `print(…, file=…)` fails to compile before any payload
# is read.
if printf '{}' | python3 -c "$script" .probe >/dev/null 2>&1; then
	# Same command substitution as the jq branch, so both strip trailing
	# newlines and the byte-for-byte contract above holds.
	out=$(printf '%s' "$payload" | python3 -c "$script" "$1")
	rc=$?
	if [ "$rc" -eq 0 ]; then
		printf '%s\n' "$out"
		exit 0
	fi
	# 4 is the script's own verdict, already explained on stderr. Anything
	# else is python3 failing after it passed the probe: report that, rather
	# than blaming the payload, and stay inside the 0/3/4 contract.
	[ "$rc" -eq 4 ] && exit 4
	echo "hook-input.sh: python3 passed its probe and then failed (exit $rc); cannot read the hook input. Install jq (apt-get install jq / brew install jq), or repair python3." >&2
	exit 3
fi

echo 'hook-input.sh: no usable JSON parser on PATH - jq is missing, unable to run, or older than the 1.5 this reader needs, and python3 is missing or unable to run; cannot read the hook input. Install or upgrade jq (apt-get install jq / brew install jq).' >&2
exit 3
