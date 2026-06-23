# AI agent harness — Copier template

A [Copier](https://copier.readthedocs.io/) template that scaffolds an
**agent-agnostic harness** based on standard practices from multiple
respected sources as of mid-2026. The harness is an `AGENTS.md`-rooted
repository layout with a thin Claude Code + OpenCode overlay enabled by
default, and everything else (Cursor, GitHub Copilot, MCP, example
ADR/skill, Claude hooks) opt-in.

The harness ships a four-phase, role-based workflow — **Product Owner**
(`/spec`) → **Architect** (`/plan`) → **Developer** (`/build`) →
**Reviewer** (`/verify`) — with one subagent definition per role under
`.agents/subagents/`. Each phase stops for user review before the next
begins, and each role declares a tool allowlist that frames its
intended scope: PO and Architect get `Read`/`Grep`/`Glob`/`Write` and
are instructed to write only under `specs/`; Developer gets full
`Read`/`Write`/`Edit`/`Grep`/`Glob`/`Bash`; Reviewer drops `Write`/`Edit`
and is instructed to run only read-only commands plus the verify
gate. Each role file carries both a Claude Code `tools:` allowlist and an
OpenCode `permission:` map, so the kind of action (read/write/edit/
bash) is tool-enforced in both surfaces. Path scoping inside `specs/`
for PO/Architect is by instruction, not enforcement — neither
`tools:` nor `permission:` supports per-path restrictions for
`Write` — so a misbehaving model could still write outside `specs/`. The pattern
follows the role-handoff conventions used by MetaGPT, BMAD Method,
GitHub Spec Kit, and CrewAI, normalised to the `AGENTS.md` + `.agents/`
layout this template already uses.

## What it generates

```
your-repo/
├─ AGENTS.md                         # canonical, ≤200 lines target
├─ CLAUDE.md                         # @AGENTS.md + Claude-Code-only stanzas
├─ README.md                         # greenfield only
├─ Makefile  OR  justfile  (or neither)  # task_runner: make | just | none
├─ .gitignore                        # greenfield: full; brownfield: merged
├─ docs/
│  ├─ architecture.md
│  ├─ style.md                        # greenfield: incl. commit-message convention
│  ├─ testing.md
│  ├─ tool-bootstrap.md               # per-package-manager install instructions
│  ├─ harness-usage.md                # unified Claude Code + OpenCode driving guide
│  └─ adr/0001-record-architecture-decisions.md   # if include_example_adr
├─ specs/                            # per-feature; YYYY-MM-example/ if opted in
├─ scripts/                          # shell entry points (if generate_scripts)
│  ├─ verify.sh                      # default implementation of verify_command (canonical lint+test gate)
│  └─ fmt-file.sh                    # per-file formatter slot for the PostToolUse hook
├─ .agents/                          # vendor-neutral shared assets
│  ├─ README.md                      # supported-agents matrix + single-source-of-truth rule
│  ├─ hooks/
│  │  ├─ block-destructive.sh        # canonical deny-list (Claude PreToolUse pipes to it)
│  │  └─ ensure-toolchain.sh         # idempotent build-tool bootstrap; if package_manager in {uv, pixi}
│  ├─ skills/verify/SKILL.md         # if include_example_skill
│  ├─ subagents/
│  │  ├─ product-owner.md            # paired with /spec
│  │  ├─ architect.md                # paired with /plan
│  │  ├─ developer.md                # paired with /build
│  │  ├─ reviewer.md                 # paired with /verify
│  │  └─ explorer.md                 # read-only investigation helper
│  └─ commands/{spec,plan,build,verify}.md
├─ .claude/                          # Claude Code (always)
│  ├─ settings.json                  # permissions (+ hooks if opted in)
│  ├─ commands/  -> ../.agents/commands       (symlink, post-gen)
│  ├─ skills/    -> ../.agents/skills         (symlink, post-gen)
│  ├─ agents/    -> ../.agents/subagents      (symlink, post-gen)
│  └─ rules/
├─ .opencode/                        # OpenCode (always)
│  ├─ opencode.jsonc
│  ├─ commands/  -> ../.agents/commands       (symlink, post-gen)
│  ├─ skills/    -> ../.agents/skills         (symlink, post-gen)
│  └─ agents/    -> ../.agents/subagents      (symlink, post-gen)
├─ .cursor/rules/project-context.mdc # if cursor
├─ .github/                          # if copilot_code_review / copilot_code_review_skill
│  ├─ copilot-instructions.md        # populated review rules (if copilot_code_review)
│  ├─ instructions/                  # path-scoped review rules (if copilot_code_review)
│  │  ├─ language.instructions.md    #   applyTo: language sources
│  │  └─ security.instructions.md    #   applyTo: ** (excludes coding agent)
│  └─ skills/code-review/SKILL.md    # if copilot_code_review_skill
└─ .mcp.json + .mcp.example.jsonc    # if mcp
```

## Usage

### Greenfield (new repo)

```sh
copier copy gh:your-org/harness-copier-template ./my-new-repo
cd my-new-repo
git init && git add -A && git commit -m "Initial harness from copier template"
```

The template asks you:

| Question                  | Notes                                                    |
| ------------------------- | -------------------------------------------------------- |
| `mode`                    | `greenfield` here. Informational only — does not change what is generated (brown-field safety is automatic via `_skip_if_exists`) |
| `project_name`            | Human-readable name                                      |
| `project_slug`            | Lowercase-dashed slug                                    |
| `project_description`     | One sentence                                             |
| `primary_language`        | Drives sensible defaults for commands                    |
| `package_manager`         | `uv` \| `pixi` \| `cmake` \| `other`; default picked from `primary_language` (python → `uv`, cpp → `cmake`, else → `other`) |
| `test_command`            | Wired into the task runner's `test` target               |
| `lint_command`            | Wired into the task runner's `lint` target               |
| `fmt_command`             | Wired into the task runner's `fmt` target                |
| `task_runner`             | `make` (default) \| `just` \| `none`                     |
| `verify_command`          | What hooks and `/verify` run; default `./scripts/verify.sh` |
| `generate_scripts`        | Generate `scripts/` placeholders (`verify.sh`, `fmt-file.sh`); default `true` |
| `license`                 | SPDX id                                                  |
| `commit_convention`       | `conventional` (default) \| `freeform`; drives the commit-message bullet in `AGENTS.md` (always updated) and the matching section in `docs/style.md` (greenfield-only — `_skip_if_exists`) |
| `pr_merge_strategy`       | `squash` (default) \| `merge` \| `rebase` \| `unknown`; tailors where the convention applies |
| `cursor`                  | Off by default                                           |
| `copilot_code_review`     | Off by default; populated Copilot code-review config under `.github/` (instructions + path-scoped rules). Copilot code review does **not** read `AGENTS.md`, so rules are restated directly |
| `copilot_code_review_skill` | Off by default; adds `.github/skills/code-review/SKILL.md` (GitHub agent-skills public preview) |
| `mcp`                     | Off by default                                           |
| `include_example_adr`     | On                                                       |
| `include_example_skill`   | On                                                       |
| `include_claude_hooks`    | On                                                       |
| `include_example_spec`    | Off by default                                           |

### Brown-field (existing repo)

```sh
cd existing-repo
copier copy gh:your-org/harness-copier-template .
```

Answer `brownfield` for the `mode` question if you like — it's informational and
doesn't change what's generated. Brown-field safety is automatic regardless of
the answer, because it comes from `_skip_if_exists`. Run into the existing repo
and the template:

- **Never silently overwrites** `README.md`, `Makefile`, `justfile`,
  `.gitignore`, `.mcp.json`, or the populated `docs/` files (`architecture`,
  `style`, `testing`, `tool-bootstrap`, `harness-usage`). They're listed in
  `_skip_if_exists` — copier leaves the existing file in place. (This also
  means switching `task_runner` later does not delete the previous file;
  remove it manually if you no longer want it.)
- **Appends** the harness's gitignore entries inside a fenced
  `# >>> ai-agent-harness >>>` … `# <<< ai-agent-harness <<<` block via the
  post-generation hook, so the operation is idempotent across re-runs.
- **Symlinks** `.claude/{skills,agents,commands}` and
  `.opencode/{skills,agents,commands}` to `.agents/{skills,subagents,commands}`
  after generation.

For files that aren't on the skip list (`AGENTS.md`, `CLAUDE.md`, the slash
commands, the Claude/OpenCode configs), Copier prompts before overwriting,
showing a diff. Pick `s` (skip), `o` (overwrite), or `u` (merge with your
editor) per-file.

### Updates

```sh
cd your-repo
copier update
```

Copier replays the answers from `.copier-answers.yml` and prompts for any
new questions added since you generated. The same `_skip_if_exists` rules
apply, and the post-gen hook re-runs idempotently.

## Repository layout

```
harness-copier-template/
├─ copier.yml         # Questions + engine config
├─ _macros.jinja      # Shared Jinja macros; lives at repo root so templates
│                     # can `{% from '_macros.jinja' import ... %}` regardless
│                     # of _subdirectory (the file itself never renders).
├─ docs/
│  └─ harness-engineering-2026-05.md  # Source report this template implements
├─ hooks/
│  └─ post_gen.py     # Idempotent .gitignore merge + symlink creation
├─ template/          # _subdirectory = "template"; everything below is rendered
│  ├─ AGENTS.md.jinja
│  ├─ CLAUDE.md.jinja
│  ├─ README.md.jinja
│  ├─ {% if task_runner == 'make' %}Makefile{% endif %}.jinja
│  ├─ {% if task_runner == 'just' %}justfile{% endif %}.jinja
│  ├─ .gitignore.jinja
│  ├─ docs/
│  ├─ specs/
│  ├─ scripts/
│  ├─ .agents/
│  ├─ .claude/
│  ├─ .opencode/
│  ├─ {% if cursor %}.cursor{% endif %}/
│  ├─ {% if copilot_code_review %}.github{% endif %}/   # copilot-instructions.md + instructions/
│  ├─ {% if copilot_code_review_skill %}.github{% endif %}/  # skills/code-review/SKILL.md
│  └─ {% if mcp %}.mcp.json{% endif %}
└─ README.md          # this file
```

Conditional dirs and files use Copier's standard Jinja-in-path technique:
the path segment renders to an empty string when the gate is false, and
Copier drops the file/dir. Note that `.jinja` (the configured
`_templates_suffix`) must stay **outside** the `{% if %}` block —
Copier strips the suffix at file-name parsing time, before the Jinja-in-path
condition is evaluated, so a path like `{% if x %}foo.jinja{% endif %}`
would keep its literal `.jinja` extension in the output.

## Choosing a task runner

`task_runner` defaults to `make` — the universal choice the source report
recommends. Pick a different value if it matches how your team already runs
tasks:

- **`make`** (default) — generate a `Makefile`. Universal toolchain, no
  extra install. Recommended when the project doesn't already have its own
  task runner.
- **`just`** — generate a `justfile` ([just.systems](https://just.systems/)).
  Cleaner syntax, no tab-sensitivity. Requires `just` on PATH.
- **`none`** — generate neither. Use this for projects whose package /
  project manager already provides task management (e.g. **pixi** tasks
  defined in `pixi.toml`, or your own external runner when
  `package_manager=other`). The harness will then surface the raw
  `test_command` / `lint_command` / `fmt_command` / `verify_command` to
  agents directly. Consider setting `verify_command` to e.g.
  `pixi run verify` to keep the Stop hook and `/verify` slash command
  pointed at your existing pipeline.

The `verify_command` answer (default `./scripts/verify.sh`) is what the
Claude Code Stop hook and the `/verify` slash command invoke. The
`scripts/` folder itself — including the default `verify.sh` and the
`fmt-file.sh` slot that the PostToolUse hook discovers — is generated
only when `generate_scripts=true`. If you disable it, make sure
`verify_command` points at a gate that does exist (e.g. `pixi run verify`).

## Provenance

This template implements **Proposal A** from the *Harness Engineering for AI
Coding Agents in 2025–2026* report ([`docs/harness-engineering-2026-05.md`](docs/harness-engineering-2026-05.md)),
which synthesises practice as of mid-2026 from:

- Anthropic Claude Code docs and engineering blog
- OpenAI Codex `AGENTS.md` spec (agents.md, donated to the Linux Foundation
  Agentic AI Foundation on 9 Dec 2025)
- OpenCode docs (sst/opencode)
- HumanLayer (Kyle Mistele, *Writing a good CLAUDE.md*; *12-Factor Agents*)
- Augment Code (*A good AGENTS.md is a model upgrade*)
- Simon Willison, Armin Ronacher, Geoffrey Huntley, Harper Reed, Eric Ma
- GitHub Engineering (analysis of 2,500+ AGENTS.md files)

## License

[MIT](LICENSE).

Note: this license covers the template repository itself. The `license`
question in `copier.yml` (default `Apache-2.0`) only sets an SPDX
identifier inside the rendered docs — it does **not** generate a LICENSE
file in downstream repos. Projects scaffolded from this template should
add their own LICENSE file separately.
