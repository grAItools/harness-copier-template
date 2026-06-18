# Changelog

All notable changes to this Copier template are recorded here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
for the questions and generated layout (a breaking change to a question
name, default, or output path bumps the major version).

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
  pixi-specific `ensure-pixi.sh`. Both scripts ship mode `0755`.
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
  helpers already present in `.claude/settings.json`
  (`ls`/`cat`/`head`/`tail`/`find`), fixing the drift between the two
  surfaces, and its deny-list comment now points at the canonical
  `.agents/hooks/block-destructive.sh`.
- `docs/tool-bootstrap.md` (uv/pixi arms) now names
  `.agents/hooks/ensure-toolchain.sh` as the canonical automated bootstrap.

### Removed

## [0.3.0] – 2026-05-28

### Added

- **Role-based subagents and `/build` command.** The harness now ships
  four role subagents under `.agents/subagents/` — `product-owner`,
  `architect`, `developer`, `reviewer` — paired 1:1 with the slash
  commands. New `/build` command for the implementation phase
  (Developer role). Existing `/spec`, `/plan`, `/verify` commands now
  delegate to their role subagent. Each role declares a tool
  allowlist matching its scope, expressed in **both** the Claude Code
  `tools:` field and the OpenCode `permission:` map so the boundary
  is tool-enforced on both surfaces: PO/Architect get
  `Read`/`Grep`/`Glob`/`Write` (no edit, no bash) and are
  *instructed* to write only under `specs/` (the path boundary is by
  prompt, not by tool permissions — neither `tools:` nor
  `permission:` is path-scoped); Developer gets full
  `Read`/`Write`/`Edit`/`Grep`/`Glob`/`Bash`; Reviewer drops
  `Write`/`Edit` entirely (a hard, tool-level guarantee against
  auto-fixing in both Claude Code and OpenCode) and pins its
  `bash:` map to the verify gate plus canonical read-only inspection
  commands with a catch-all `"*": deny` (same shape used for
  `explorer`). Pattern follows MetaGPT, BMAD Method, GitHub Spec
  Kit, and CrewAI conventions. See
  [`docs/decisions/0003-role-based-subagents-and-build-command.md`](docs/decisions/0003-role-based-subagents-and-build-command.md).
- New question **`commit_convention`** (`conventional` | `freeform`,
  default `conventional`) — surfaces Conventional Commits 1.0.0
  guidance in `docs/style.md` and a pointer in `AGENTS.md`.
- New question **`pr_merge_strategy`** (`squash` | `merge` | `rebase` |
  `unknown`, default `squash`) — tailors the commit-message guidance to
  where the convention actually has to hold (PR title vs. every branch
  commit).
- New file **`docs/tool-bootstrap.md`** — always-generated, pre-filled
  per `package_manager` with install snippets for the curated set
  (`uv`, `pixi`, `cmake`) plus a generic `_Fill in:_` arm for `other`.
  Includes an "Activate the language toolchain" section that gives
  [`mise`](https://mise.jdx.dev/) and [`asdf`](https://asdf-vm.com/)
  equal billing as runtime version managers, plus a verification step
  that uses the runner-aware `cmd('verify')` macro. Added to
  `_skip_if_exists` so brown-field repos keep their existing file.
- `AGENTS.md` `## Stack` section gets a "New-machine setup" pointer to
  the new doc.

### Removed (breaking)

- `include_example_subagent` Copier question. The `explorer` subagent
  it used to gate is now always generated, because the Developer
  role's working loop relies on `explorer` being present.
  Brownfield repos that previously generated with
  `include_example_subagent: false` will get `.agents/subagents/explorer.md`
  added on their next `copier update`. Saved answers files still
  containing `include_example_subagent: …` can keep the key (Copier
  ignores unknown answers) or remove it by hand.
- `package_manager` choices narrowed from 21 options to a curated set:
  `uv` (Python), `pixi` (conda-ecosystem), `cmake` (C/C++), and
  `other`. Removed: `pip`, `poetry`, `pdm`, `hatch`, `conda`, `pnpm`,
  `npm`, `yarn`, `bun`, `cargo`, `go`, `gradle`, `maven`, `dotnet`,
  `meson`, `bazel`, `make`. Pick `other` for anything not in the
  curated set and fill in the install steps in
  `docs/tool-bootstrap.md` after generation. Existing projects on
  `copier update` that previously selected a removed value must
  re-answer the question with one of the new choices.
- `test_command` / `lint_command` / `fmt_command` defaults: arms for
  the removed package managers / languages were dropped; the
  remaining recognised combinations are `python+uv`, `python+pixi`,
  and `cpp+cmake`. Everything else falls through to
  `echo 'TODO: configure ..._command in copier.yml'`.

### Changed

- The `AGENTS.md` commit-message bullet is now a one-line orientation
  that names the convention plus a merge-strategy-specific clause
  (e.g. "apply the format to the **PR title** (squash-merge)") and
  defers the full format, type list, breaking-change syntax,
  examples, and merge-strategy detail to
  [`docs/style.md#commit-messages`](docs/style.md#commit-messages). Keeps AGENTS.md
  short (it's the always-loaded agent instruction surface) and puts
  the detail in the document people open when they actually need it.
- The `AGENTS.md` `## Stack` section's tool-versions and
  new-machine-setup bullets collapse to a single referrer pointing at
  [`docs/tool-bootstrap.md`](docs/tool-bootstrap.md); the pin-file
  trade-off (`.tool-versions` vs. `mise.toml`) lives only in
  `docs/tool-bootstrap.md` now.
- Default behaviour: new projects render with Conventional Commits +
  squash-merge guidance.

### Upgrade notes

- `AGENTS.md` is *not* in `_skip_if_exists`, so existing projects
  running `copier update` will see a diff on it (accept it to pick
  up the shorter commit-message bullet and the new
  `docs/tool-bootstrap.md` referrer).
- `docs/style.md` *is* in `_skip_if_exists`. For greenfield repos it
  is generated with a `## Commit messages` section, which is what
  `AGENTS.md` now links to. For brownfield repos whose existing
  `docs/style.md` does not have that section, the AGENTS.md link
  will land on the file but not on a section — merge the new
  template `docs/style.md` (or copy the section across by hand) so
  the link resolves. The `commit_convention` question's help text
  also calls this out at prompt time.
- `docs/tool-bootstrap.md` is always generated on greenfield and added
  to `_skip_if_exists` for brownfield, matching the existing
  `docs/architecture.md` / `docs/style.md` / `docs/testing.md` pattern.

## [0.2.0] – 2026-05-21

### Added

- New question **`task_runner`** (`make` | `just` | `none`, default
  `make`) that selects the task-runner file the template generates.
  See [ADR 0001](docs/decisions/0001-decouple-task-runner-and-scripts.md)
  for the rationale.
- New question **`verify_command`** (default `./scripts/verify.sh`).
  Drives the Claude Code `Stop` hook and the `/verify` slash command;
  for `task_runner=none` it is the actual verify entry point.
- New question **`generate_scripts`** (boolean, default `true`).
  Controls whether the `scripts/` folder is populated with placeholders
  for the harness's shell-entry-point slots. Initial placeholder set:
  `scripts/verify.sh` (canonical lint+test gate) and
  `scripts/fmt-file.sh` (per-file formatter slot the Claude Code
  `PostToolUse` hook already discovers via `test -x`).
- Shared `_macros.jinja` partial at the repo root exposing
  `cmd(target)`, `has_cmd(target)`, and `runner_file_name()` so every
  agent-facing surface renders the same command form for the chosen
  runner.
- ADR 0001 documenting the rationale for decoupling the task runner
  and the `scripts/` folder from agent-facing wording.

### Changed

- Slash command definitions (`/spec`, `/plan`, `/verify`) now live at
  `.agents/commands/` and are symlinked into `.claude/commands/` and
  `.opencode/commands/` by the post-generation hook, matching how
  skills and subagents already work. The `.opencode/commands/README.md`
  workaround that asked OpenCode users to flip the symlink direction by
  hand is gone. See [ADR 0002](docs/decisions/0002-canonicalize-commands-under-agents.md)
  for the rationale. Brownfield repos with an existing
  `.claude/commands/` directory must move their command files into
  `.agents/commands/` and delete the old directory before the symlink
  can be created.
- The Claude Code `Stop` hook now invokes the `task_runner`-aware
  `cmd('verify')` (e.g. `make verify` / `just verify` / the raw
  `verify_command`) instead of bypassing the runner with a fixed
  `./scripts/verify.sh`. The hook's `INPUT` payload is now piped to
  `jq` via `printf '%s' "$INPUT"` rather than unquoted `echo $INPUT`,
  so payloads containing whitespace, globs, or shell metacharacters
  are passed through literally.
- The OpenCode and Claude Code permission allowlists are now
  conditional on `task_runner` (`Bash(make:*)` / `Bash(just:*)` /
  omitted) instead of always listing `make`.
- Agent-facing surfaces (AGENTS.md, CLAUDE.md, README, the verify
  skill, the `/verify` slash command, `docs/testing.md`, the example
  spec's `tasks.md`) now render their command examples from the shared
  macro instead of hard-coded `make <target>` strings.
- The post-copy "Next steps" message now prints the user-facing
  invocation (`make verify` / `just verify` / the raw `verify_command`
  for `task_runner=none`) so the runner wiring is exercised during the
  smoke test rather than being bypassed.
- `hooks/post_gen.py` now parses `.copier-answers.yml` with PyYAML
  (already a Copier dependency), catches `yaml.YAMLError`, validates
  that the root is a `dict` and that values are `str` scalars, and
  normalizes newlines to spaces (preserving other internal whitespace)
  before rendering the answer in the printed next-step line.
- Renamed `docs/harness-engineering-report.md` →
  `docs/harness-engineering-2026-05.md` to make the dated provenance
  explicit and leave room for follow-up reports.

### Removed

- The old `generate_verify_script` question is replaced by the broader
  `generate_scripts` (default unchanged at `true`). Existing projects
  running `copier update` will be prompted for the new key once; the
  generated behaviour is identical when the new key is `true`.

## [0.1.0] – 2026-05-19

### Added

- Initial release of the template. Implements Proposal A from
  [`docs/harness-engineering-2026-05.md`](docs/harness-engineering-2026-05.md):
  a short root `AGENTS.md`, a `CLAUDE.md` import overlay, a
  `docs/` hierarchy (`architecture.md`, `style.md`, `testing.md`,
  `adr/`), an optional `specs/<date>-<slug>/` convention, a
  `Makefile` with `test` / `lint` / `fmt` / `verify` targets, an
  optional `scripts/verify.sh` entry point, and thin tool-specific
  overlays for Claude Code (`.claude/`), OpenCode (`.opencode/`),
  Cursor (`.cursor/`), and GitHub Copilot (`.github/`).
- Brownfield-safe defaults: `README.md`, `Makefile`, `.gitignore`,
  `.mcp.json`, and the populated `docs/` files are protected by
  `_skip_if_exists`.
- Post-generation hook (`hooks/post_gen.py`) that idempotently
  merges a managed block of agent-related entries into an existing
  `.gitignore` and symlinks shared agent assets (`skills/`,
  `subagents/`) into `.claude/` and `.opencode/`.

[Unreleased]: https://github.com/grAItools/harness-copier-template/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/grAItools/harness-copier-template/releases/tag/v0.3.0
[0.2.0]: https://github.com/grAItools/harness-copier-template/releases/tag/v0.2.0
[0.1.0]: https://github.com/grAItools/harness-copier-template/releases/tag/v0.1.0
