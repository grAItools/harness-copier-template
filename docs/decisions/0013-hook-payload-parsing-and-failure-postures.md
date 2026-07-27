# 13. Hook payload parsing via a fallback reader, with explicit per-hook failure postures

## Status

Accepted (2026-07-27). Extends ADR 0004 (canonical agent hooks); prompted by
issue #31.

## Context

The generated Claude Code hooks (`.claude/settings.json`) read their JSON
payloads with `jq`, which was an undocumented hard requirement: nothing in the
generated repo declared it, `ensure-toolchain.sh` neither installed nor checked
it, and each of the three call sites degraded differently — and silently —
when `jq` was missing:

- **PreToolUse (Bash guard)**: `c=$(jq …) || exit 2` denied *every* Bash call,
  including the `apt-get install jq` that would fix it, with no message beyond
  the shell's `jq: not found`. The session was unusable from the first tool
  use. (The pre-#20 wiring had the opposite defect: the pipeline's exit status
  made a missing `jq` fail *open*, letting destructive commands through
  unchecked.)
- **Stop (verify gate)**: the `stop_hook_active` early-exit read `""` and never
  fired, defeating the guard that exists to stop the Stop hook from
  re-triggering itself — a red verify gate could loop indefinitely.
- **PostToolUse (formatter)**: the trailing `|| true` swallowed the failure;
  auto-format-on-edit silently stopped working while the docs kept telling
  users to rely on it.

`block-destructive.sh` also exited 2 without saying what it matched, so a
legitimate deny and an infrastructure failure were indistinguishable to the
agent, whose recovery for both is to reword and retry.

Two directions were considered: document `jq` and make every deny path print a
message (keeps the hard dependency; the Stop and PostToolUse silent
degradations remain), or remove the hard dependency with a fallback parser.
Regex-based extraction (`sed`) was rejected: `.tool_input.command` routinely
contains escaped quotes that regexes mishandle. A degraded mode that greps the
*raw JSON payload* when no parser exists was also rejected: it can
false-positive on the payload's `description` field and silently changes the
guard's semantics.

## Decision

1. **One canonical payload reader, `.agents/hooks/hook-input.sh`.** All three
   hooks read fields through it. It parses with `jq` when available, falls
   back to `python3` (booleans normalised to `true`/`false` so callers are
   parser-agnostic), and exits 3 with a message when neither is on PATH —
   letting each caller distinguish "cannot read the input" from "field is
   empty" and apply its own posture.
2. **Explicit, legible failure postures per hook** when no parser is
   available:
   - *PreToolUse*: **fail closed** — deny with a message naming the cause and
     the remedy (install `jq` from a shell outside the agent). Every other
     deny path (guard script missing, empty command) also gets a message.
   - *Stop*: **fail open** — `exit 0` with a `verify skipped:` note, mirroring
     the existing package-manager-unavailable posture. Running verify without
     a readable `stop_hook_active` risks the infinite loop; skipping the gate
     does not.
   - *PostToolUse*: **fail open** (unchanged) but with a `fmt skipped:` note
     so the degradation is visible.
3. **`block-destructive.sh` names the pattern it matched** on stderr before
   exiting 2.
4. **SessionStart warns** (never aborts) when neither `jq` nor `python3` is on
   PATH, so the problem surfaces before the first Bash denial. The
   SessionStart hook now renders for every `include_claude_hooks` project;
   the `ensure-toolchain.sh` entry within it stays gated on uv/pixi.
5. **The requirement is documented** in `development/tool-bootstrap.md`
   (gated on `include_claude_hooks`) and in the `include_claude_hooks`
   question help.

## Consequences

- On the common `jq`-less developer hosts (macOS, stock Linux distributions —
  both usually ship `python3`), all three hooks work out of the box.
- On hosts with neither parser, the Bash guard still refuses to run unchecked
  commands (fail-closed is preserved), but the denial now explains itself and
  the session start warns before the first Bash call.
- `hook-input.sh` ships unconditionally (like `block-destructive.sh`); it is
  inert unless a hook calls it.
- `development/tool-bootstrap.md` is `_skip_if_exists`-protected, so existing
  downstream repos do not receive the new "Required tools" bullet on
  `copier update`; the settings/hook fixes themselves do land.
- The deny-list grep itself still fails open if `grep` breaks; `grep` is
  POSIX-mandated and assumed present everywhere `sh` is, unlike `jq`.
