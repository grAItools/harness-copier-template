# Changelog

All notable changes to this Copier template are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/spec/v2.0.0.html) over the questions and generated
layout (a breaking change to a question name, default, or output path bumps the
major version).

## [Unreleased]

### Added

- Role playbook skills: `.agents/skills/{product-owner,architect,developer,reviewer}-playbook/`
  plus a shared `.agents/skills/design-principles/` (design ground rules and a
  red-flag checklist distilled from *A Philosophy of Software Design*, *The
  Pragmatic Programmer*, *Domain-Driven Design*, and *The Design of Design*).
  Each role subagent now reads its playbook before acting; the Reviewer's
  playbook adds review depth without overriding the verdict/gate rules. See
  [ADR 0011](docs/decisions/0011-knowledge-grounded-role-playbooks.md).
- `development/glossary.md` — the project's ubiquitous language; added to
  `_skip_if_exists` and to the `development/README.md` index. Like the
  decision register in `development/adr/README.md`, it is a **register**, not
  a trunk-gated prose doc: entries accrete mid-feature through one channel
  only (promotion from a reviewed spec's Glossary section at `/spec`
  wrap-up), the Reviewer's scope check verifies each new entry against the
  spec that proposed it, and renames or meaning changes of existing entries
  stay trunk-gated. The **Document liveness** table gains rows for both
  registers (ADR 0011).
- `development/work/<YYYY-MM>-<slug>/report.md` joins the feature lifecycle — the durable
  account of what actually happened (what was built, declared deviations,
  negative results, escalated decisions, follow-ups, gate result), written by
  the Developer as work happens, audited for honesty by the Reviewer, frozen
  at merge. `AGENTS.md`, the example spec directory, `/build`, `/verify`, and
  the `developer`/`reviewer` subagents gain matching instructions. Adapted
  from the ICON-sc project's per-work-unit reports. See
  [ADR 0007](docs/decisions/0007-feature-report-and-document-liveness.md).
- `AGENTS.md` states an authority order for document conflicts
  (`development/architecture.md` > `spec.md` > `plan.md` > `tasks.md`) with the rule
  that contradictions are recorded in `report.md`, never silently resolved;
  `development/harness-usage.md` gains a **Document liveness** table saying when each
  harness file freezes (ADR 0007).
- Decision-escalation protocol: a decision beyond an agent's authority becomes
  a `DECISION-PENDING:` line in `report.md` plus a row in the new decision
  register (a section of the generated `development/adr/README.md`, with an
  ADR-vs-register rule of thumb); the reviewer enforces the same-PR
  register-row contract per diff, and the register alone records outcomes
  once reports freeze. `development/adr/README.md` joins `_skip_if_exists` so a
  populated downstream register is never overwritten. See
  [ADR 0008](docs/decisions/0008-decision-register-and-escalation-marker.md).
- New question **`pr_template`** (bool, default `true`) — generates
  `.github/PULL_REQUEST_TEMPLATE.md`, a definition-of-done checklist tied to
  the harness (gate green, spec criteria evidenced, `report.md` written, no
  weakened tests, `DECISION-PENDING:` lines registered). Added to
  `_skip_if_exists`; independent of the `copilot_*` questions. See
  [ADR 0009](docs/decisions/0009-pr-template-question.md).
- `development/testing.md` gains a **Reading gate output** section: passed counts may
  only grow, new skips are findings to explain, never narrow the gate
  (`-x`/`-k`/`--ignore`/marker edits) to make it pass; the
  `developer`/`reviewer` subagents carry matching rules.
- `development/README.md` — always-generated one-line index of the process
  memory tree, the `development/` ↔ `docs/` boundary statement, and the
  trunk-gated rule (harness docs are living but changed via a dedicated PR,
  never silently mid-feature). The Document liveness table carries the same
  rule. Adopted from ICON-sc's `policies/` rationale *instead of* a
  `policies/` folder — see
  [ADR 0010](docs/decisions/0010-development-tree-and-work-folder.md).
- `docs/proposals/0001-adopt-icon-sc-process-memory-practices.md` and
  `docs/proposals/0002-development-tree-and-work-folder.md` — the evaluations
  of ICON-sc's harness this release implements (P9, a freeze-guard hook, is
  deferred), plus `docs/decisions/README.md` — ADR index + this repo's own
  decision register.

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
- `development/harness-usage.md` — unified Claude Code + OpenCode driving guide; added
  to `_skip_if_exists`.
- OpenCode native `formatter` (when `generate_scripts=true`) — routes edits
  through `scripts/fmt-file.sh`, disabling the conflicting built-in per
  `primary_language`, for parity with the Claude Code `PostToolUse` hook.
- `development/style.md` gains a `## Changelog` section (and an `AGENTS.md` Conventions
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
- Comment-hygiene policy: `development/style.md` gains a `## Comments` section
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
- The Developer's mid-build hand-backs are now serviced, not just emitted.
  `/build` gains a step 5 that runs the `explorer` pass an
  `EXPLORER-REQUEST: [phase <n>]` line asks for, appends the answer (citations
  intact) as `EXPLORER-FINDING:` and re-invokes the developer — three rounds
  per phase, mirroring the `SPIKE-REQUEST:`/`SPIKE-FINDING:` protocol `/plan`
  already had — and a step 6 for the two mid-phase stops it never handled: a
  `DECISION-PENDING:` escalation (answer, re-invoke, register row) and a new
  `PLAN-REVISION:` marker routing a wrong plan back to `/plan`, not `/verify`.
  The `developer` subagent's Handoff names all four hand-back stops with their
  markers, and `development/harness-usage.md`'s Phase-3 section sets the
  expectation for the human driving it.

### Changed

- Generated docs mark their fill-in points with one consistent set of
  scaffold markers: `_Fill in: …_` for blocks the downstream user replaces
  (greppable), bare `<placeholder>` inline — angle brackets, never
  backticked, the same form the role subagents emit in their output
  formats — and `>` blockquotes reserved for durable how-this-doc-works
  notes. The PR template keeps HTML comments deliberately (its prompts are
  re-filled by every PR author and must not render). Documented in
  `development/README.md` and the template README.
- The `spec.md` skeleton gains two mandatory sections: `## Constraints` (with a
  `Budgeted resource:` line naming the scarce thing trade-offs must respect) and
  `## Glossary` (terms pinned during the discussion, promoted to
  `development/glossary.md` after review). Both are wired to readers: the
  architect compares its design alternatives on the budgeted resource and stops
  rather than relaxing it, and the reviewer's spec-conformance axis now fails a
  phase that exceeds a constraint or leaves the budget unmeasured, however green
  the success criteria are. In-flight specs written to the old skeleton lack
  both sections (ADR 0011).
- The `plan.md` skeleton changes with the architect's de-risking rules: the
  Architecture decisions block gains a `Considered:` (design-it-twice) line and
  plans gain an optional `## Spike findings` section. `/plan` gains a spike loop
  — the architect writes a `SPIKE-REQUEST:` line in `scratch.md` and hands back,
  the main agent runs the throwaway experiment and appends a `SPIKE-FINDING:`
  line, capped at three rounds — and Phase 1 now defaults to a tracer bullet for
  cross-layer features. The architect gains `Edit` (it appends to the shared
  `scratch.md` rather than overwriting it) and reads `scratch.md` alongside
  `spec.md`. Downstream repos' example `plan.md` carries the old skeleton
  (ADR 0011).
- The Product Owner's "stop and ask **one** clarifying question before writing
  anything" rule is replaced by a multi-round interrogation protocol: look up
  whatever the repo can answer, then stop on the single highest-value remaining
  question, carrying a recommended answer. `/spec` relays the reply and
  re-invokes the subagent (capped at five rounds) until nothing blocking is
  left. The handoff instruction travels in the subagent's own reply, so the loop
  survives description-match invocation without the slash command. Expect a
  dialogue where the old harness stopped after one question (ADR 0011).
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
  and the populated `development/` files).
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
- `development/tool-bootstrap.md` (uv/pixi arms) names
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
- `development/adr/README.md` gains a "When to write one" section — the single
  home for the ADR criteria (a decision must be hard to reverse, surprising
  without context, *and* a real trade-off; trivial or easily reversed choices get
  none). The `AGENTS.md` Do/Don't notes, the `development/harness-usage.md`
  decision guide, the architect subagent, and the Copilot review rules
  (`copilot-instructions.md`, `skills/code-review/SKILL.md`) point to it instead
  of restating the criteria or implying every dependency/persistence/auth choice
  needs an ADR.

### Fixed

- The `reviewer` subagent read `plan.md`'s **Review checklist** as unbounded
  instructions ("it is part of your instructions", no precedence clause, unlike
  the two neighbouring inputs). The checklist is now **additive only**: it may
  add checks, never narrow the review or relax a verdict rule, and an entry that
  tries is a MINOR finding against the plan, whose fix belongs to `/plan`. Scope
  the plan explicitly *grants* is unaffected. `/verify`, the `architect` subagent
  (the role that writes the checklist), the example `plan.md`, and
  `development/harness-usage.md` (`_skip_if_exists` — see **Upgrade notes**)
  restate the bound, which extends to `plan.md` the non-override principle that
  [ADR 0011](docs/decisions/0011-knowledge-grounded-role-playbooks.md) §2 states
  for the reviewer playbook.
- `hooks/post_gen.py` merges the `.gitignore` managed block **per entry**
  instead of skipping it wholesale once the fence marker is present. Previously
  it returned early on any existing block, so an entry added by a later template
  version — `AGENTS.local.md`, below — could never reach a repo generated from
  an older one, despite the docstring and `README.md` promising an append-only
  merge. Entries a user commented out inside the fence are left alone, and
  nothing outside the fence is touched. A **half-open fence** (a begin marker
  whose end marker was hand-deleted) is now warned about and left alone;
  previously it read as "no block at all" and a second block was appended,
  leaving two begin markers and pulling every line between them inside the
  managed fence. The merge also preserves line endings byte for byte — a
  CRLF `.gitignore` stays CRLF instead of being rewritten to LF, so the
  `copier update` diff shows only the inserted entries.
- `AGENTS.local.md` is now ignored in brown-field repos too: it was present in
  the greenfield `.gitignore` but missing from the managed block appended by
  `hooks/post_gen.py`.
- The `architect` subagent could not execute its own spike protocol: one
  constraint told it to write the spike question to `scratch.md` while another
  allowed it to write only `plan.md` and `tasks.md`, so an architect reading the
  narrower rule silently planned on the untested assumption instead. The write
  allowance now names `scratch.md`, and the hand-back contract lives in the
  subagent's Handoff section, where description-match invocation still reaches
  it.
- The `developer` subagent must re-run the verification gate when its
  end-of-phase red-flag rework touches code. The rework step sat after the
  gate-green step in the working loop, so a phase could hand off reporting
  "gate: green" for a tree that no longer passed — which the Reviewer ranks
  MAJOR as a false report claim.
- `development/harness-usage.md` no longer gates every mention of skills on
  `include_example_skill`. Five skills (four role playbooks plus
  `design-principles`) ship unconditionally and the subagents require reading
  them, but with the example skill declined the guide told the reader the
  project had no skills at all.
- `development/harness-usage.md`'s Phase-1 prompting section no longer promises
  "expect _one_ clarifying question", which the Product Owner protocol above
  contradicts; it documents the question loop and its round cap instead. The
  file is in `_skip_if_exists`, so downstream repos need the correction applied
  by hand.
- The `reviewer-playbook` skill no longer tells the Reviewer that "praise is not
  padding" — the `reviewer` subagent forbids padding the verdict with praise,
  and the playbook is explicitly subordinate to it.
- `development/glossary.md` was in `_skip_if_exists` but missing from the
  brown-field protected-file lists in `README.md` and the `copier.yml` header
  comment, so an adopter with an existing glossary had no way to know it would
  be skipped without a prompt or diff.
- The `design-principles` skill is referenced by its full
  `.agents/skills/design-principles/SKILL.md` path in the developer and reviewer
  playbooks, matching every other reference.
- `CLAUDE.md` no longer claims hook enforcement when `include_claude_hooks=false`
  (the hooks stanza is now gated, matching `harness-usage.md`), and the example
  `verify` skill's Stop-hook gotcha is gated the same way. `CLAUDE.md`'s
  skill-invocation example now names a role playbook (always generated) instead
  of the optional `verify` skill.
- The example `development/work/YYYY-MM-example/` files match the output
  formats the subagents write: `spec.md` gains the missing
  **Users & stakeholders** and **Open questions** sections and the Product
  Owner's section order; `plan.md` gains **Risks & open questions**; the
  `tasks.md` note no longer suggests merging straight after a green gate
  (the feature merges on `/verify` GO) or "archiving" the gitignored
  `scratch.md`.
- `.agents/subagents/README.md` no longer says a subagent hands back "via the
  slash command that invoked it" — hand-back protocols travel in the
  subagent's own reply (Handoff sections), which is what keeps them alive
  under description-match invocation; `explorer` states its clarifying
  question the same stop-and-return way.
- `development/harness-usage.md`'s Phase-2 section sets the spike-loop
  expectation (`SPIKE-REQUEST:` hand-backs, three rounds max), matching the
  dialogue expectation Phase 1 already documents.
- `harness-usage.md` no longer calls `.claude/rules/` "currently empty" — the
  comment-hygiene fragment always ships there.
- Claude Code `PostToolUse`/`PreToolUse` hooks in `.claude/settings.json` now
  read input from the JSON payload on **stdin** via `jq` (reading
  `.tool_input.file_path` and `.tool_input.command`) instead of the nonexistent
  `$CLAUDE_TOOL_INPUT_FILE_PATH` / `$CLAUDE_TOOL_INPUT` env vars, which left
  format-on-save and destructive-command blocking (`rm -rf`, `git push --force`,
  `git reset --hard`) silently no-opping. The `PreToolUse` guard fails closed
  (exit 2) when `jq` errors or the extracted command is empty. `copier update`
  propagates the fix (not in `_skip_if_exists`).
- Hand-back loops are now bounded where they run, not only in the slash
  command that starts them. The `/spec` five-round and `/plan` three-round caps
  were the loops' only termination condition, in the one file both subagents
  say may never have been read ("do not assume the caller loaded `/spec`"). The
  `architect` subagent now states its own three-spike cap and counts the
  `SPIKE-REQUEST:` lines already in `scratch.md`; the `product-owner`, which
  cannot write `scratch.md`, numbers each question ("question 2 of at most 5")
  and asks the caller to carry the count; and `AGENTS.md` — the one file loaded
  on every path, including description match — gains a "hand-back loops are
  bounded" rule with a default cap of three for any role that states none.

### Removed (breaking)

- **The generated harness's process memory moves into a single top-level
  `development/` tree, and `docs/` is no longer generated.** Every generated
  `docs/` file moves: `docs/{architecture,style,testing,tool-bootstrap,harness-usage}.md`
  → `development/…`, `docs/adr/` → `development/adr/`; and `specs/` →
  `development/work/` ("specs" named one file kind of the five the folder now
  holds). `docs/` stays reserved for the project's own user documentation, the
  way `src/` is for sources — the `development/` tree is repo-internal and
  never published. All agent surfaces (`AGENTS.md`, subagents, commands,
  `.opencode` instructions, `.claude/rules`, Copilot seeds, `.gitignore`
  scratch pattern, post-gen gitignore block, PR template) are retargeted. See
  [ADR 0010](docs/decisions/0010-development-tree-and-work-folder.md).
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

- **`docs/` → `development/` migration (existing generated repos):** before
  running `copier update`, move the harness files so Copier tracks them at
  their new paths instead of re-creating them alongside the old ones:

  ```sh
  mkdir -p development
  git mv docs/architecture.md docs/style.md docs/testing.md \
         docs/tool-bootstrap.md docs/harness-usage.md docs/adr development/
  git mv specs development/work        # only works if specs/ has committed
                                       # content; a generated-but-empty specs/
                                       # is untracked — just `rmdir specs`
                                       # (development/work/ is created on the
                                       # next /spec)
  rmdir docs 2>/dev/null || true       # keep docs/ if it has your own user docs
  copier update
  ```

  Then **delete** the stale `specs/*/scratch.md` line from your `.gitignore`'s
  managed block. The post-gen hook adds `development/work/*/scratch.md` for you
  (it merges the block per entry, so a missing entry is appended), but it never
  removes anything — and `.gitignore` is `_skip_if_exists`, so the template
  render won't clean it up either. Leaving the old line is harmless but
  misleading. Expect the other `_skip_if_exists`-preserved files to keep old-path
  prose after migration — `README.md`'s specs mention, and any paths inside a
  PR template you already had (the *generated* `.github/PULL_REQUEST_TEMPLATE.md`
  is new in this release and already points at `development/`) — update those
  by hand, and be ready to resolve `copier update` merge conflicts inside the
  moved `development/` files (the example ADR is a known case).
- `development/tool-bootstrap.md` is in `_skip_if_exists`, so a brownfield `copier
  update` keeps its existing copy and won't pick up the `ensure-toolchain.sh`
  reference — merge it by hand (the bootstrap and hook wiring work without it).
- `development/harness-usage.md` is in `_skip_if_exists` too, so an existing
  repo keeps its copy and will still promise "expect _one_ clarifying question"
  from `/spec`, still describe skills as conditional on the example skill, say
  nothing about `/plan` spike round-trips or `/build` explorer round-trips,
  still call `plan.md`'s **Review checklist** unbounded "extra instructions",
  and still lack the register rows in the **Document liveness** table. Diff it
  against the template version and merge the changed sections (Phase-1
  dialogue, Phase-2 spikes, Phase-3 explorer round-trips, skills prose, Phase-4
  checklist bound, liveness registers) by hand; the agents themselves follow
  the (updated, not skip-listed) `.agents/` files either way, so the risk is a
  confused human, not a confused agent.
- The `architect` subagent now declares `Edit` / `permission.edit: allow` so it
  can append to `scratch.md` instead of overwriting it. If you pinned or
  hand-edited `.agents/subagents/architect.md`, re-apply the frontmatter change;
  an architect left on `Write`-only will clobber prior spike findings and
  Developer hand-back notes, and `scratch.md` is gitignored, so they're gone.
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
