# Changelog

All notable changes to this Copier template are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/spec/v2.0.0.html) over the questions and generated
layout (a breaking change to a question name, default, or output path bumps the
major version).

## [Unreleased]

### Added

- `specs/<YYYY-MM>-<slug>/report.md` joins the feature lifecycle — the durable
  account of what actually happened (what was built, declared deviations,
  negative results, escalated decisions, follow-ups, gate result), written by
  the Developer as work happens, audited for honesty by the Reviewer, frozen
  at merge. `AGENTS.md`, the example spec directory, `/build`, `/verify`, and
  the `developer`/`reviewer` subagents gain matching instructions. Adapted
  from the ICON-sc project's per-work-unit reports. See
  [ADR 0007](docs/decisions/0007-feature-report-and-document-liveness.md).
- `AGENTS.md` states an authority order for document conflicts
  (`docs/architecture.md` > `spec.md` > `plan.md` > `tasks.md`) with the rule
  that contradictions are recorded in `report.md`, never silently resolved;
  `docs/harness-usage.md` gains a **Document liveness** table saying when each
  harness file freezes (ADR 0007).
- Decision-escalation protocol: a decision beyond an agent's authority becomes
  a `DECISION-PENDING:` line in `report.md` plus a row in the new decision
  register (a section of the generated `docs/adr/README.md`, with an
  ADR-vs-register rule of thumb); the reviewer enforces the same-PR
  register-row contract per diff, and the register alone records outcomes
  once reports freeze. `docs/adr/README.md` joins `_skip_if_exists` so a
  populated downstream register is never overwritten. See
  [ADR 0008](docs/decisions/0008-decision-register-and-escalation-marker.md).
- New question **`pr_template`** (bool, default `true`) — generates
  `.github/PULL_REQUEST_TEMPLATE.md`, a definition-of-done checklist tied to
  the harness (gate green, spec criteria evidenced, `report.md` written, no
  weakened tests, `DECISION-PENDING:` lines registered). Added to
  `_skip_if_exists`; independent of the `copilot_*` questions. See
  [ADR 0009](docs/decisions/0009-pr-template-question.md).
- `docs/testing.md` gains a **Reading gate output** section: passed counts may
  only grow, new skips are findings to explain, never narrow the gate
  (`-x`/`-k`/`--ignore`/marker edits) to make it pass; the
  `developer`/`reviewer` subagents carry matching rules.
- `docs/proposals/0001-adopt-icon-sc-process-memory-practices.md` — the
  evaluation of ICON-sc's harness this release implements (P9, a freeze-guard
  hook, is deferred), plus `docs/decisions/README.md` — ADR index + this
  repo's own decision register.

- `.agents/hooks/block-destructive.sh` (always generated, mode `0755`) — the
  canonical destructive-command deny-list; the Claude Code `PreToolUse(Bash)`
  hook calls it fail-closed instead of carrying an inline `grep`. See
  [ADR 0004](docs/decisions/0004-canonical-agent-hooks-and-toolchain-bootstrap.md).
- `.agents/hooks/ensure-toolchain.sh` (generated only for `uv`/`pixi`, mode
  `0755`) — idempotent build-tool bootstrap, wired into the Claude Code
  `SessionStart` hook (install if missing); the `Stop` hook exports it onto PATH
  for the verify gate.
- `.agents/README.md` — supported-agents matrix (Claude Code, OpenCode,
  Copilot, Codex, Gemini CLI, natively-`AGENTS.md` agents), the add-an-agent
  recipe, and the single-source-of-truth rule.
- `docs/harness-usage.md` — unified Claude Code + OpenCode driving guide; added
  to `_skip_if_exists`.
- OpenCode native `formatter` (when `generate_scripts=true`) — routes edits
  through `scripts/fmt-file.sh`, disabling the conflicting built-in per
  `primary_language`, for parity with the Claude Code `PostToolUse` hook.
- `docs/style.md` gains a `## Changelog` section (and an `AGENTS.md` Conventions
  pointer) on writing concise Keep-a-Changelog entries in generated projects.
- New question **`copilot_code_review_skill`** (bool, default `false`) —
  generates a Copilot agent skill at `.github/skills/code-review/SKILL.md`.
  GitHub agent skills for code review are a public preview (since June
  2026), so it is off by default. Independent of `copilot_code_review`,
  but most useful with it on.
- New **`.github/instructions/`** seed files, gated on
  `copilot_code_review`: `language.instructions.md` (`applyTo:` glob
  derived from `primary_language`) and `security.instructions.md`
  (`applyTo: "**"`, `excludeAgent: "coding-agent"` to keep it out of the
  coding agent). Copilot code review reads these from the PR's base branch.
- `primary_language` gains **`fortran`** and **`julia`** choices, and the
  `cpp` glob now covers CUDA (`.cu`/`.cuh`). Command defaults for the new
  languages fall through to the generic `other` arm (TODO placeholders) —
  fill them in after generation.
- Comment-hygiene policy: `docs/style.md` gains a `## Comments` section
  (comments describe the code, not the review/release process), a new
  path-scoped `.claude/rules/comments.md` (`paths:` from `primary_language`)
  surfaces it at edit time, and `AGENTS.md`, the `developer`/`reviewer`
  subagents, and the Copilot `language.instructions.md` seed gain matching
  pointers. Backported from preserf #110; enforcement tooling (ruff
  `ERA`/`FIX`, a guard test) is left to downstream. See
  [ADR 0006](docs/decisions/0006-comment-hygiene-policy.md).
- `_macros.jinja` gains a `lang_glob()` macro (the `primary_language` →
  source-glob map, previously inline in `language.instructions.md.jinja`),
  now shared by that file and `.claude/rules/comments.md`.

### Changed

- The `reviewer` subagent is hardened to a skeptical-review protocol: scope
  check first (`git diff --stat`; out-of-plan touches are defects), never
  trust the Developer's narrative (re-run the gate, re-derive claims), probe
  that new tests can fail (vacuous tests are MAJOR defects), audit `report.md`
  honesty (undeclared deviations are defects), and rank findings
  MAJOR / MINOR / INFO — any MAJOR means NEEDS-WORK.
- The `architect` subagent writes plans "for an agent with less context":
  `plan.md` gains **Invariants** (non-negotiables restated inline) and
  **Review checklist** (feature-specific checks the reviewer consumes)
  sections, mirrored in the example spec directory and read by `/verify`.
- Clarified that the `mode` question is informational only — it does not change
  what is generated. Its `copier.yml` help text and the `README.md` brown-field
  section no longer imply that answering `brownfield` is what enables file
  skipping; brown-field safety comes unconditionally from `_skip_if_exists`. The
  `copier.yml` header comment now lists the full protected set (adds `.mcp.json`
  and the populated `docs/` files).
- `AGENTS.md` gains "Driving the harness" and "Supported agents" links, plus a
  `uv`/`pixi` auto-bootstrap "Do" note.
- `.opencode/opencode.jsonc` allow-list adds `ls`/`cat`/`head`/`tail` to match
  `.claude`; its deny globs use `*…*` substring form (`*rm -rf*`, `*push --force*`,
  `*reset --hard*`, `*DROP TABLE*`) for real parity with `block-destructive.sh`.
  `.claude/settings.json`'s deny broadens `git reset --hard origin:*` to
  `git reset --hard:*` (Claude permission syntax is prefix-anchored, so it can't
  fully match the substring globs — `block-destructive.sh` is the canonical guard
  when hooks are on).
- `find` is dropped from every bash allow-list — the `.claude`/`.opencode`
  surfaces and the `explorer`/`reviewer` subagent scopes — because its
  `-delete`/`-exec rm` forms are not read-only and bypass the deny-list.
- `docs/tool-bootstrap.md` (uv/pixi arms) names
  `.agents/hooks/ensure-toolchain.sh` as the canonical automated bootstrap;
  the installer URL/command and bin dir live in `_macros.jinja` macros so the
  script, the Stop-hook PATH export, and the doc can't drift.
- The Copilot review seed rules (`copilot-instructions.md`,
  `instructions/*.instructions.md`, `skills/code-review/SKILL.md`) now lead
  with scientific-computing / HPC / ML concerns — numerical stability,
  reproducibility, precision/dtype, vectorization, GPU/MPI resource use,
  and unsafe deserialization of model checkpoints — instead of the
  previous web-app emphasis (SQL injection, request handlers, IDOR). Web
  /service-security rules are retained but scoped to service code.

### Fixed

- Claude Code `PostToolUse`/`PreToolUse` hooks in `.claude/settings.json` now
  read input from the JSON payload on **stdin** via `jq` (reading
  `.tool_input.file_path` and `.tool_input.command`) instead of the nonexistent
  `$CLAUDE_TOOL_INPUT_FILE_PATH` / `$CLAUDE_TOOL_INPUT` env vars, which left
  format-on-save and destructive-command blocking (`rm -rf`, `git push --force`,
  `git reset --hard`) silently no-opping. The `PreToolUse` guard fails closed
  (exit 2) when `jq` errors or the extracted command is empty. `copier update`
  propagates the fix (not in `_skip_if_exists`).

### Removed (breaking)

- **Renamed question `copilot` → `copilot_code_review`.** The old name
  suggested broader scope than the feature has; Copilot code review is the
  surface this configures. Existing repos must rename the key in
  `.copier-answers.yml` before `copier update`, or re-answer the prompt.
- **`.github/copilot-instructions.md` is now a populated review-rules
  file, not a one-line redirect to `AGENTS.md`.** Copilot code review does
  not read `AGENTS.md` (confirmed by GitHub docs and community discussion
  #174058), and does not follow deep import chains, so a redirect silently
  propagated nothing. The file now carries the review-relevant subset of
  the conventions directly, within Copilot code review's 4,000-character
  per-file cap (target ≤ 3,500 chars).

### Upgrade notes

- `docs/tool-bootstrap.md` is in `_skip_if_exists`, so a brownfield `copier
  update` keeps its existing copy and won't pick up the `ensure-toolchain.sh`
  reference — merge it by hand (the bootstrap and hook wiring work without it).
- The `copilot` question was renamed to `copilot_code_review`. Existing
  projects must rename the key in `.copier-answers.yml` (or delete it and
  re-answer the prompt) **before** running `copier update` — otherwise the
  stored answer is dropped and the question re-prompts with its default
  (`false`), silently turning the feature off.
- If you had `copilot: true`, the generated
  `.github/copilot-instructions.md` changes from a one-line redirect to a
  populated review-rules file, and `.github/instructions/` is added.
  `copier update` shows a diff on `copilot-instructions.md`; accept it to
  pick up the review rules, then trim the seeded rules to your project.
- See [ADR 0005](docs/decisions/0005-copilot-code-review-gate.md) for the
  rationale behind the rename and the populated-rules layout.

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
