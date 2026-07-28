# AI agent harness — Copier template

A [Copier](https://copier.readthedocs.io/) template that scaffolds an
**agent-agnostic harness** based on standard practices from multiple
respected sources as of mid-2026. The harness is an `AGENTS.md`-rooted
repository layout with a thin Claude Code + OpenCode overlay enabled by
default; GitHub Copilot code review is opt-in, and the PR template and
Claude Code hooks are opt-out.

The harness ships a four-phase, role-based workflow — **Product Owner**
(`/spec`) → **Architect** (`/plan`) → **Developer** (`/build`) →
**Reviewer** (`/verify`) — with one subagent definition per role under
`.agents/subagents/`. Each phase stops for user review before the next
begins, and each role declares a tool allowlist that frames its
intended scope: PO and Architect get `Read`/`Grep`/`Glob`/`Write` and
are instructed to write only under `development/work/`; Developer gets full
`Read`/`Write`/`Edit`/`Grep`/`Glob`/`Bash`; Reviewer drops `Write`/`Edit`
and is instructed to run only read-only commands plus the verify
gate. Each role file carries both a Claude Code `tools:` allowlist and an
OpenCode `permission:` map, so the kind of action (read/write/edit/
bash) is tool-enforced in both surfaces. Path scoping inside `development/work/`
for PO/Architect is by instruction, not enforcement — neither
`tools:` nor `permission:` supports per-path restrictions for
`Write` — so a misbehaving model could still write outside it. The pattern
follows the role-handoff conventions used by MetaGPT, BMAD Method,
GitHub Spec Kit, and CrewAI, normalised to the `AGENTS.md` + `.agents/`
layout this template already uses.

Each role file carries its **method** inline, grounded in a shared
`design-principles` skill (`.agents/skills/design-principles/`) — a
distillation of Ousterhout's *A Philosophy of Software Design*, Hunt &
Thomas's *The Pragmatic Programmer*, Evans's *Domain-Driven Design*, and
Brooks's *The Design of Design*: the Product Owner interrogates one
question at a time with recommended answers and grows a project glossary
(`development/glossary.md`); the Architect designs twice, spikes risky
assumptions (via a main-agent hand-back), and plans a tracer-bullet
first phase; the Developer writes contracts and interface comments first
and self-checks against a red-flag list; the Reviewer probes change
amplification and hunts absent artifacts. See ADRs 0011 and 0012.

The loop leaves a durable audit trail: each feature directory ends with a
`report.md` (what was built, declared deviations, negative results,
follow-ups) that freezes at merge, and decisions beyond an agent's authority
are escalated as `DECISION-PENDING:` lines into a decision register in
`development/adr/README.md` instead of being silently resolved. The Reviewer
audits the report for honesty and re-runs the gate itself. All process memory
lives in a single `development/` tree — `docs/` is never generated and stays
reserved for the project's own user documentation, the way `src/` is for
sources. These conventions are adapted from the ICON-sc project's process
memory (see ADRs 0007–0010).

## What it generates

```
your-repo/
├─ AGENTS.md                         # canonical, ≤200 lines target
├─ CLAUDE.md                         # @AGENTS.md + Claude-Code-only stanzas
├─ README.md                         # greenfield only
├─ Makefile  OR  justfile  (or neither)  # task_runner: make | just | none
├─ .gitignore                        # greenfield: full; brownfield: merged
├─ development/                      # repo process memory (docs/ is NOT generated:
│  │                                 # it stays reserved for user documentation)
│  ├─ README.md                       # one-line index of the tree + docs boundary
│  ├─ architecture.md
│  ├─ style.md                        # greenfield: incl. commit-message convention
│  ├─ glossary.md                     # ubiquitous language; starts empty, grows via specs
│  ├─ testing.md
│  ├─ tool-bootstrap.md               # per-package-manager install instructions
│  ├─ harness-usage.md                # unified Claude Code + OpenCode driving guide
│  ├─ adr/                            # ADRs + decision register (README.md)
│  │  └─ 0001-record-architecture-decisions.md    # seed ADR (always)
│  └─ work/                           # per-feature spec/plan/tasks/report[/scratch]
├─ scripts/                          # generated iff verify_command mentions scripts/verify.sh
│  ├─ verify.sh                      # default implementation of verify_command (canonical lint+test gate)
│  └─ fmt-file.sh                    # per-file formatter slot for the PostToolUse hook
├─ .agents/                          # vendor-neutral shared assets
│  ├─ README.md                      # supported-agents matrix, single-source rule, layout docs
│  ├─ hooks/
│  │  ├─ block-destructive.sh        # canonical deny-list (Claude PreToolUse pipes to it)
│  │  ├─ hook-input.sh               # hook payload reader: jq, python3 fallback
│  │  └─ ensure-toolchain.sh         # idempotent build-tool bootstrap; if package_manager in {uv, pixi}
│  ├─ skills/
│  │  └─ design-principles/SKILL.md  # shared design ground rules + red-flag checklist
│  ├─ subagents/                     # each role file carries its method inline
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
│  └─ rules/comments.md             # comment-hygiene policy (paths: by language)
├─ .opencode/                        # OpenCode (always)
│  ├─ opencode.jsonc
│  ├─ commands/  -> ../.agents/commands       (symlink, post-gen)
│  ├─ skills/    -> ../.agents/skills         (symlink, post-gen)
│  └─ agents/    -> ../.agents/subagents      (symlink, post-gen)
└─ .github/                          # if pr_template / copilot_code_review
   ├─ PULL_REQUEST_TEMPLATE.md       # definition-of-done checklist (if pr_template)
   ├─ copilot-instructions.md        # populated review rules (if copilot_code_review)
   ├─ instructions/                  # path-scoped review rules (if copilot_code_review)
   │  ├─ language.instructions.md    #   applyTo: language sources
   │  └─ security.instructions.md    #   applyTo: ** (excludes coding agent)
   └─ skills/code-review/SKILL.md    # Copilot review skill (if copilot_code_review)
```

## Usage

### Greenfield (new repo)

```sh
copier copy gh:your-org/harness-copier-template ./my-new-repo
cd my-new-repo
git init && git add -A && git commit -m "Initial harness from copier template"
```

The template asks you (13 questions):

| Question                  | Notes                                                    |
| ------------------------- | -------------------------------------------------------- |
| `project_name`            | Human-readable name                                      |
| `project_description`     | One sentence                                             |
| `primary_language`        | Drives sensible defaults for commands                    |
| `package_manager`         | `uv` \| `pixi` \| `cmake` \| `other`; default picked from `primary_language` (python → `uv`, cpp → `cmake`, else → `other`) |
| `test_command`            | Wired into the task runner's `test` target               |
| `lint_command`            | Wired into the task runner's `lint` target               |
| `fmt_command`             | Wired into the task runner's `fmt` target                |
| `task_runner`             | `make` (default) \| `just` \| `none`                     |
| `verify_command`          | What hooks and `/verify` run; default `./scripts/verify.sh`. `scripts/` (`verify.sh` + `fmt-file.sh`) is generated exactly when this answer names `scripts/verify.sh` as a path — no separate question; existing copies are `_skip_if_exists`-protected |
| `commit_convention`       | `conventional` (default) \| `freeform`; drives the commit-message bullet in `AGENTS.md` (always updated) and the matching section in `development/style.md` (greenfield-only — `_skip_if_exists`) |
| `copilot_code_review`     | Off by default; populated Copilot code-review config under `.github/` (instructions + path-scoped rules + the code-review agent skill). Copilot code review does **not** read `AGENTS.md`, so rules are restated directly |
| `pr_template`             | On by default; adds `.github/PULL_REQUEST_TEMPLATE.md`, a definition-of-done checklist tied to the harness (gate, spec evidence, `report.md`, decision register). Inert for non-GitHub remotes |
| `include_claude_hooks`    | On by default. Hooks read their JSON payloads via `.agents/hooks/hook-input.sh` (`jq`, `python3` fallback, each probed by *running* it); with no working parser, SessionStart warns, the Bash guard fails closed with an explanatory message, and the Stop gate runs but only reports a red result |

### Brown-field (existing repo)

```sh
cd existing-repo
copier copy gh:your-org/harness-copier-template .
```

Brown-field safety is automatic, because it comes from `_skip_if_exists`. Run
into the existing repo and the template:

- **Never silently overwrites** `README.md`, `Makefile`, `justfile`,
  `.gitignore`, `scripts/verify.sh`, `scripts/fmt-file.sh`,
  `.github/PULL_REQUEST_TEMPLATE.md`,
  `development/adr/README.md` (it accumulates decision-register rows), or the
  populated `development/` files (`architecture`, `style`, `testing`,
  `tool-bootstrap`, `harness-usage`, `glossary`). They're listed in
  `_skip_if_exists` — copier leaves the existing file in place. (This also
  means switching `task_runner` later does not delete the previous file;
  remove it manually if you no longer want it.)
- **Appends** the harness's gitignore entries inside a fenced
  `# >>> ai-agent-harness >>>` … `# <<< ai-agent-harness <<<` block via the
  post-generation hook. It merges per entry, not per block: a re-run or a
  `copier update` adds only the entries the block is missing, so a repo
  generated from an older version picks up newly added ones. An entry you
  comment out inside the block stays commented out, and nothing outside the
  fence is touched.
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
│  ├─ development/    # incl. adr/ and work/ (the per-feature lifecycle)
│  ├─ {% if generate_scripts %}scripts{% endif %}/   # gated on the derived generate_scripts value
│  ├─ .agents/
│  ├─ .claude/
│  ├─ .opencode/
│  ├─ {% if pr_template %}.github{% endif %}/   # PULL_REQUEST_TEMPLATE.md
│  └─ {% if copilot_code_review %}.github{% endif %}/   # copilot-instructions.md + instructions/ + skills/code-review/
└─ README.md          # this file
```

Conditional dirs and files use Copier's standard Jinja-in-path technique:
the path segment renders to an empty string when the gate is false, and
Copier drops the file/dir. Note that `.jinja` (the configured
`_templates_suffix`) must stay **outside** the `{% if %}` block —
Copier strips the suffix at file-name parsing time, before the Jinja-in-path
condition is evaluated, so a path like `{% if x %}foo.jinja{% endif %}`
would keep its literal `.jinja` extension in the output.

### Scaffold markers in generated docs

Generated documents that the downstream user completes use three markers,
consistently: `_Fill in: …_` for a block to replace (delete the marker;
greppable via `rg 'Fill in:'`), bare `<placeholder>` — angle brackets,
never backticked — for inline substitution, and `>` blockquotes for durable
notes about how a document works — those stay. The bare form matches the
output formats the role subagents are instructed to emit, so a scaffold and
a freshly written document are the same shape; the cost is that a Markdown
preview may swallow `<word>` as an unknown HTML tag, which these
repo-internal, read-as-text files accept. The generated
`.github/PULL_REQUEST_TEMPLATE.md` is the deliberate exception: it uses
HTML comments, because its prompts are re-filled by every PR author and
must not show in the rendered PR description.

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
exactly when the answer names `scripts/verify.sh` as a path (so
`bash ./scripts/verify.sh` still counts while `./build-scripts/verify.sh`
does not; internally a derived, never-asked `generate_scripts` value in
`copier.yml`). Point `verify_command` at a project-native gate (e.g.
`pixi run verify`) and no `scripts/` is generated. Existing
`scripts/verify.sh` / `fmt-file.sh` files are never overwritten
(`_skip_if_exists`), and a stale `generate_scripts` value supplied as
data triggers a post-copy warning instead of a silently broken gate.

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

Note: this license covers the template repository itself. The template
does **not** generate a LICENSE file in downstream repos (the rendered
docs carry a `_Fill in: SPDX identifier_` marker instead). Projects
scaffolded from this template should add their own LICENSE file
separately.
