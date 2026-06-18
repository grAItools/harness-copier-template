# Changelog

All notable changes to this Copier template are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/spec/v2.0.0.html) over the questions and generated
layout (a breaking change to a question name, default, or output path bumps the
major version).

## [Unreleased]

### Added

- **Canonical agent-hook scripts under `.agents/hooks/`.** New
  `block-destructive.sh` (always generated) is the single source of truth
  for the destructive-command deny-list; the Claude Code `PreToolUse(Bash)`
  hook now pipes the command through it instead of carrying an inline
  `grep`. New `ensure-toolchain.sh` (generated only when
  `package_manager` is `uv` or `pixi`, which have a one-line installer)
  idempotently bootstraps the build tool; it is wired into the Claude Code
  `SessionStart` hook and the `Stop` hook self-heals through it before
  running the gate. Backports preserf PR #114, generalized from its
  pixi-specific `ensure-pixi.sh`. Both scripts ship mode `0755`. See
  [ADR 0004](docs/decisions/0004-canonical-agent-hooks-and-toolchain-bootstrap.md).
- **New file `.agents/README.md`** — supported-agents matrix (Claude Code,
  OpenCode, Copilot, OpenAI Codex, Google Gemini CLI, and natively-`AGENTS.md`
  agents), the recipe for adding an agent, and the single-source-of-truth
  rule (folds in the principle from preserf's ADR 0007 without shipping a
  numbered ADR — numbering belongs to each consumer repo). Codex needs no
  file (reads root `AGENTS.md`); Gemini wiring is documented as a one-file
  stub rather than a new question.
- **New file `docs/harness-usage.md`** — a unified Claude Code + OpenCode
  harness guide (four-phase loop, the five subagents, the three trigger
  mechanisms, per-phase prompting, and a tool-comparison table), rendered
  through the `cmd()` macro and gated on `include_claude_hooks`,
  `generate_scripts`, `include_example_skill`, and the commit-convention
  answers. Added to `_skip_if_exists`. Backports preserf PR #113.
- **OpenCode auto-format.** `.opencode/opencode.jsonc` gains a native
  `formatter` block (when `generate_scripts=true`) that routes edits
  through the same `scripts/fmt-file.sh` entry point Claude Code's
  PostToolUse hook uses, with the conflicting built-in formatter disabled
  per `primary_language`. Backports preserf PR #113.

### Changed

- `AGENTS.md` gains "Driving the harness" and "Supported agents" entries in
  the "Where things live" list, and (for `uv`/`pixi` with
  `include_claude_hooks`) a "Do" note that the toolchain is auto-bootstrapped
  at session start.
- `.opencode/opencode.jsonc` permission allow-list adds the read-only
  helpers `ls`/`cat`/`head`/`tail` to match `.claude/settings.json`, and its
  deny-list comment now points at the canonical
  `.agents/hooks/block-destructive.sh` (described as the approximate,
  prefix-only mirror it is). `find` is deliberately **not** allow-listed on
  either surface — `find -delete` / `-exec rm` would bypass the deny-list —
  so `Bash(find:*)` was also dropped from `.claude/settings.json`.
- `docs/tool-bootstrap.md` (uv/pixi arms) now names
  `.agents/hooks/ensure-toolchain.sh` as the canonical automated bootstrap.

### Removed

### Upgrade notes

- `docs/tool-bootstrap.md` is in `_skip_if_exists`, so a brownfield repo
  running `copier update` keeps its existing copy and will **not** pick up
  the new `.agents/hooks/ensure-toolchain.sh` reference automatically. If you
  want it, merge the template's `docs/tool-bootstrap.md` by hand (the new
  bootstrap script and Claude `SessionStart`/`Stop` wiring still work without
  it).

## [0.3.0] – 2026-05-28

### Added

- **Role-based subagents + `/build` command.** Four roles under
  `.agents/subagents/` (`product-owner`, `architect`, `developer`, `reviewer`)
  paired 1:1 with the slash commands; `/spec`/`/plan`/`/verify` now delegate to
  their role. Each role's tool allowlist is enforced in both the Claude Code
  `tools:` field and the OpenCode `permission:` map: PO/Architect get
  read+`Write` (no edit/bash, instructed to write only under `specs/` — by
  prompt, not path-scoped); Developer gets full read/write/edit/bash; Reviewer
  drops `Write`/`Edit` and pins `bash:` to the verify gate plus read-only
  commands with `"*": deny`. See
  [ADR 0003](docs/decisions/0003-role-based-subagents-and-build-command.md).
- Question **`commit_convention`** (`conventional` | `freeform`, default
  `conventional`) — drives commit guidance in `docs/style.md` and `AGENTS.md`.
- Question **`pr_merge_strategy`** (`squash` | `merge` | `rebase` | `unknown`,
  default `squash`) — targets the commit-message guidance at where it applies
  (PR title vs. every branch commit).
- File **`docs/tool-bootstrap.md`** — always generated, pre-filled per
  `package_manager` (`uv`/`pixi`/`cmake`, generic arm for `other`), with a
  toolchain-activation section (`mise`/`asdf`) and a `cmd('verify')` check.
  Added to `_skip_if_exists`; `AGENTS.md` `## Stack` points to it.

### Removed (breaking)

- Question `include_example_subagent`. The `explorer` subagent is now always
  generated (the Developer loop depends on it); brownfield repos gain
  `.agents/subagents/explorer.md` on next `copier update`.
- `package_manager` narrowed to `uv`, `pixi`, `cmake`, `other` (was 21
  options). Projects on a removed value must re-answer on `copier update`.
- `test_command`/`lint_command`/`fmt_command` defaults now only cover
  `python+uv`, `python+pixi`, `cpp+cmake`; everything else falls through to a
  `TODO` placeholder.

### Changed

- `AGENTS.md` commit-message bullet is now a one-line, merge-strategy-aware
  pointer to [`docs/style.md#commit-messages`](docs/style.md#commit-messages),
  keeping the always-loaded surface short.
- `AGENTS.md` `## Stack` collapses tool-version/setup detail into a single
  pointer to `docs/tool-bootstrap.md`.
- New projects default to Conventional Commits + squash-merge guidance.

### Upgrade notes

- `AGENTS.md` is not in `_skip_if_exists` — expect a diff on `copier update`
  (accept it for the new bullet + bootstrap pointer).
- `docs/style.md` is in `_skip_if_exists`; brownfield repos lacking a
  `## Commit messages` section should merge it in so the `AGENTS.md` link
  resolves.
- `docs/tool-bootstrap.md`: greenfield-generated, brownfield-skipped, matching
  the other `docs/` files.

## [0.2.0] – 2026-05-21

### Added

- Question **`task_runner`** (`make` | `just` | `none`, default `make`) —
  selects the generated runner file. See
  [ADR 0001](docs/decisions/0001-decouple-task-runner-and-scripts.md).
- Question **`verify_command`** (default `./scripts/verify.sh`) — drives the
  Claude Code `Stop` hook and `/verify`; the real entry point when
  `task_runner=none`.
- Question **`generate_scripts`** (default `true`) — populates `scripts/` with
  `verify.sh` (lint+test gate) and `fmt-file.sh` (the `PostToolUse` formatter
  slot).
- `_macros.jinja` at repo root exposing `cmd()`, `has_cmd()`,
  `runner_file_name()` so every surface renders the same command form.

### Changed

- Slash commands canonicalized under `.agents/commands/` and symlinked into
  `.claude/`/`.opencode/` by the post-gen hook (matching skills/subagents).
  See [ADR 0002](docs/decisions/0002-canonicalize-commands-under-agents.md).
  Brownfield repos must move existing `.claude/commands/` files into
  `.agents/commands/` first.
- `Stop` hook now runs the runner-aware `cmd('verify')` and pipes its payload
  via `printf '%s' "$INPUT" | jq` (safe for whitespace/metacharacters).
- Permission allowlists are conditional on `task_runner`
  (`Bash(make:*)`/`Bash(just:*)`/omitted).
- All agent-facing surfaces render command examples from the shared macro
  instead of hard-coded `make <target>`.
- Post-copy "Next steps" prints the real invocation so runner wiring is
  smoke-tested.
- `hooks/post_gen.py` parses `.copier-answers.yml` with PyYAML (validates
  dict/str, normalizes newlines).
- Renamed `docs/harness-engineering-report.md` →
  `docs/harness-engineering-2026-05.md`.

### Removed

- Question `generate_verify_script`, superseded by `generate_scripts` (same
  default; identical behaviour when `true`).

## [0.1.0] – 2026-05-19

### Added

- Initial release. Implements Proposal A from
  [`docs/harness-engineering-2026-05.md`](docs/harness-engineering-2026-05.md):
  a short root `AGENTS.md`, a `CLAUDE.md` import overlay, a `docs/` hierarchy
  (`architecture.md`, `style.md`, `testing.md`, `adr/`), optional
  `specs/<date>-<slug>/`, a `Makefile` (`test`/`lint`/`fmt`/`verify`), an
  optional `scripts/verify.sh`, and thin overlays for Claude Code, OpenCode,
  Cursor, and GitHub Copilot.
- Brownfield-safe `_skip_if_exists`: `README.md`, `Makefile`, `.gitignore`,
  `.mcp.json`, and the populated `docs/` files.
- Post-gen hook (`hooks/post_gen.py`) — idempotent `.gitignore` merge +
  symlinks of shared agent assets into `.claude/`/`.opencode/`.

[Unreleased]: https://github.com/grAItools/harness-copier-template/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/grAItools/harness-copier-template/releases/tag/v0.3.0
[0.2.0]: https://github.com/grAItools/harness-copier-template/releases/tag/v0.2.0
[0.1.0]: https://github.com/grAItools/harness-copier-template/releases/tag/v0.1.0
