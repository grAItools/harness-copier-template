# 13. Hook payload parsing via a fallback reader, with explicit per-hook failure postures

## Status

Accepted (2026-07-27). Extends ADR 0004 (canonical agent hooks); prompted by
issue #31. Decisions 1 and 2 amended by
[ADR 0014](0014-reader-scalar-contract-and-stop-gate-posture.md) — see it for
the reader's current (scalar-only) parity contract, the run-probe on both
backends, and the Stop hook's report-don't-skip posture.

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
   hooks read fields through it. It parses with `jq` when available, falling
   back to `python3` — probed by *running* it, not `command -v` alone, because
   stock macOS ships a `/usr/bin/python3` Command Line Tools stub that passes
   `command -v` but fails at runtime. Output is backend-identical ('' for
   null/absent or a path through a non-object, `true`/`false` for booleans,
   JSON for objects/arrays), and failures are distinguished by exit code:
   3 when no working parser is on PATH, 4 for an empty or unparseable
   payload — letting each caller diagnose the actual cause rather than
   guessing.
2. **Explicit, legible failure postures per hook**, branching on the reader's
   exit code:
   - *PreToolUse*: **fail closed** on any read failure — exit 3 denies with
     the install-`jq` remedy (from a shell outside the agent); any other
     failure denies naming the real cause (payload unreadable or the reader
     itself damaged) instead of blaming missing parsers. Every other deny
     path (guard script missing, empty command) also gets a message.
   - *Stop*: **fail open** — skip the gate rather than risk the infinite
     loop — but with **exit 1** (non-blocking error), not 0: Claude Code
     surfaces non-zero stderr to the user, while exit-0 stderr is visible
     only in transcript mode. The package-manager-unavailable skip adopts
     the same exit-1 posture. The bootstrap variant exports the toolchain
     bin dir onto PATH *before* reading the payload, so a parser installed
     only there (uv-managed python3, `pixi global install jq`) is visible.
   - *PostToolUse*: **fail open** with the same visible `exit 1` +
     `fmt skipped:` note.
3. **`block-destructive.sh` reports that the command matched the destructive
   deny-list** (listing its patterns) on stderr before exiting 2. The deny
   decision deliberately stays on POSIX `grep -qE`: extracting the specific
   match with `grep -o` was rejected because `-o` is a non-POSIX extension
   and GNU grep suppresses `-o` stdout for binary-classified input while
   still matching — either way the extraction-as-decision would fail open.
4. **SessionStart warns** when no working parser is present, so the problem
   surfaces before the first Bash denial — with exit 1 for the same
   visibility reason (still non-blocking; the session continues). The
   SessionStart hook now renders for every `include_claude_hooks` project;
   the `ensure-toolchain.sh` entry within it stays gated on uv/pixi.
5. **The requirement is documented** in `development/tool-bootstrap.md`
   (gated on `include_claude_hooks`) and in the `include_claude_hooks`
   question help.

## Consequences

- On the common `jq`-less developer hosts, all three hooks work out of the
  box: stock Linux distributions ship `python3`, and macOS does once the
  Xcode Command Line Tools are installed (the usual developer baseline —
  and the pre-CLT stub is detected as *absent* by the run-probe, not
  misdiagnosed as a parser failure).
- On hosts with neither parser, the Bash guard still refuses to run unchecked
  commands (fail-closed is preserved), but the denial now explains itself and
  the session start warns before the first Bash call.
- `hook-input.sh` ships unconditionally (like `block-destructive.sh`); it is
  inert unless a hook calls it.
- `development/tool-bootstrap.md` is `_skip_if_exists`-protected, so existing
  downstream repos do not receive the new "Required tools" bullet on
  `copier update`; the settings/hook fixes themselves do land.
- The deny-list grep itself still fails open if `grep` breaks; `grep -qE` is
  POSIX-mandated and assumed present everywhere `sh` is, unlike `jq`.
- The deny message names the deny-list rather than the specific matched
  pattern — the price of keeping the deny decision on POSIX `-q` (see
  Decision 3); with four patterns, the list is short enough to be legible.
