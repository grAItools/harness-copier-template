# 3. Role-based subagents and `/build` command

## Status

Accepted (2026-05-27). Partially superseded by
[ADR 0004](0004-canonical-agent-hooks-and-toolchain-bootstrap.md): `find` is no
longer one of the read-only inspection commands (its `-delete`/`-exec` forms are
not read-only), so disregard its mention in the Decision below.

## Context

The harness already shipped three slash commands — `/spec`, `/plan`,
and `/verify` — that map cleanly onto distinct phases of the
software-engineering loop: define, design, and review. Each phase
produces a structured artifact (`spec.md`, `plan.md`, and a
verification verdict respectively) that the next phase consumes.

What the harness did **not** ship:

- An explicit name for the *role* responsible for each phase. The
  commands inlined their behavioural rules ("WHAT and WHY only", "each
  phase has tests", "never silently skip a failing test") into the
  command file, so the same rules had to be re-discovered every time
  the user re-read the command.
- A command for the build phase itself. The implicit assumption was
  that the user would just "do the work" between `/plan` and `/verify`,
  with no equivalent role-scoped boundary, tool allowlist, or
  hand-off contract.
- A read-only **Reviewer** scope. `/verify` ran the gate but did not
  separate "did the gate pass" from "does the work actually match
  what the Product Owner asked for".

Every well-known multi-agent framework solves this with explicit
role-scoped agents:

- **MetaGPT** (Hong et al., arXiv 2308.00352) — PM / Architect /
  Engineer / QA, with strict artifact handoffs.
- **BMAD Method** (bmad-code-org) — Analyst / PM / Architect / PO /
  SM / Dev / QA, each in its own markdown file with `critical_actions`,
  `commands`, and named handoff artifacts.
- **GitHub Spec Kit** (github.com/github/spec-kit) — `/specify` →
  `/plan` → `/tasks` → `/implement`, each producing a Markdown
  artifact that feeds the next.
- **CrewAI** (docs.crewai.com) — role / goal / backstory triad per
  agent.

The harness already had the artifacts and most of the commands; it
just lacked the role definitions and the build-phase command.

## Decision

Add four role-based subagent definitions under `.agents/subagents/`,
ungated, paired 1:1 with the slash commands:

| Slash command | Role          | Subagent          | Tools                              |
|---------------|---------------|-------------------|------------------------------------|
| `/spec`       | Product Owner | `product-owner.md`| Read, Grep, Glob, Write            |
| `/plan`       | Architect     | `architect.md`    | Read, Grep, Glob, Write            |
| `/build` *(new)* | Developer  | `developer.md`    | Read, Write, Edit, Grep, Glob, Bash|
| `/verify`     | Reviewer      | `reviewer.md`     | Read, Grep, Glob, Bash             |

Add the new `/build` slash command under `.agents/commands/` (which
the existing post-gen hook already symlinks into `.claude/commands/`
and `.opencode/commands/` per [ADR 0002](0002-canonicalize-commands-under-agents.md)).

Each existing command (`/spec`, `/plan`, `/verify`) is rewritten to
delegate to its role subagent. The command files keep just the
directory-selection / pre-flight logic; the behavioural contract
(output format, "stop and ask" boundaries, tool scope, handoff rule)
lives in the subagent definition where it belongs.

Concretely:

- New: `template/.agents/subagents/{product-owner,architect,developer}.md`
  and `template/.agents/subagents/reviewer.md.jinja` (the reviewer
  is templated to render the `cmd('verify')` macro into its
  `permission.bash` allowlist).
- New: `template/.agents/commands/build.md.jinja`.
- Updated: `template/.agents/commands/{spec,plan,verify}.md.jinja`
  delegate to their role subagent.
- Updated: `template/AGENTS.md.jinja` and `template/CLAUDE.md.jinja`
  list the four role agents and the four slash commands.
- Updated: the project `README.md` documents the role workflow and
  the new subagent file list.

The role subagents ship **unconditionally** — no new Copier question.
They are the canonical implementation of the slash commands the
harness already promises; gating them would mean a user who turned
the flag off would get commands that delegate to subagents that
don't exist.

The `explorer.md` subagent — previously gated by
`include_example_subagent` — is also promoted to ship
unconditionally, and the `include_example_subagent` question is
removed from `copier.yml`. Rationale: the Developer role's working
loop explicitly recommends delegating wide searches to `explorer`,
so making it optional would introduce the same "command references a
file that may not exist" hazard the role agents avoid. The
read-only-investigation pattern that `explorer.md` illustrates is
better learnt by reading the always-present file than by being
optionally absent. Brownfield repos that previously generated with
`include_example_subagent: false` will get `explorer.md` added on
their next `copier update`.

## Consequences

**Positive.**

- Symmetry with the dominant patterns in the field (MetaGPT, BMAD,
  Spec Kit, CrewAI). Users coming from any of those frameworks find
  the same role names, the same artifact handoffs, and the same
  stop-and-ask boundaries.
- Tighter tool scoping per role, enforced on both target surfaces.
  Each role file carries both a Claude Code `tools:` allowlist and
  an OpenCode `permission:` map, so the **kind** of action available
  (read vs. write vs. edit vs. bash) is enforced at the tool level
  in both Claude Code and OpenCode. The Reviewer's `Write`/`Edit`
  denial is a true hard guarantee in both tools that the role
  cannot auto-fix defects, and its `bash:` map further restricts
  shell execution to the verify gate and the canonical read-only
  inspection commands (`rg`, `grep`, `ls`, `find`, `cat`, `head`,
  `tail`, `wc`, `git log`/`diff`/`blame`/`show`/`status`) with a
  catch-all `"*": deny`. The Developer's allowlist makes its full
  edit + bash scope explicit. The Product Owner and Architect get
  read+write but no edit/bash, and are *instructed* (in the role
  prose) to write only under `specs/`. Note that neither Claude
  Code's `tools:` allowlist nor OpenCode's `permission:` map
  supports per-path restrictions for `Write`, so the
  PO-/Architect-only-writes-to-`specs/` boundary is enforced by
  prompt, not by tool permissions — a misbehaving model could still
  write elsewhere.
- Each role's behavioural contract lives in one place
  (`.agents/subagents/<role>.md`), not duplicated across command
  files and `AGENTS.md`. Future changes to a role's rules are a
  one-file edit.
- File ownership per role is aligned with OpenCode's `write` vs.
  `edit` permission split: each artifact is created (via `write`,
  which both PO and Architect have) by the role that owns it — PO
  writes `spec.md`, Architect writes `plan.md` and `tasks.md`,
  Developer writes `scratch.md`. `/spec` only creates the spec
  directory; pre-creating empty stubs would force later roles to
  `edit` files they should be able to `write` from scratch under
  OpenCode's permission model.
- The build phase now has the same shape as the other three phases:
  a slash command, a role agent, an explicit handoff. The implicit
  "just do the work" gap is closed.
- Frontmatter carries both the Claude Code allowlist (`tools:`) and
  the OpenCode permission map (`permission:` with `read`/`write`/
  `edit`/`bash` allow/deny entries) alongside the shared
  `name`/`description`/`model` keys. Each tool reads the field it
  understands and ignores the other (Claude Code does not parse
  `permission:`; OpenCode treats `tools:` as deprecated and uses
  `permission:` — see `docs/harness-engineering-2026-05.md:175-194`).
  Every subagent also declares `mode: subagent` (OpenCode-only;
  Claude Code ignores it). Without that key OpenCode defaults to
  `mode: all`, which would expose the role as a top-level primary
  agent in addition to a delegated one — the explicit `mode:
  subagent` keeps each role as a delegation-only helper. This keeps
  a single subagent file working in both tools via the existing
  symlink layout, while ensuring the Reviewer's `Write`/`Edit`
  denial is enforced on both surfaces — not just Claude Code.

**Negative.**

- The default harness now ships five files under
  `.agents/subagents/` (four role agents + the always-present
  `explorer`), up from one optional `explorer` previously. This is
  the trade-off for making the role boundaries explicit and removing
  the gating hazard.
- `copier update` on previously-generated repos will prompt for
  overwrites on `AGENTS.md`, `CLAUDE.md`, and the three existing
  command files. The `_skip_if_exists` list does not protect these
  files (by design — they are core agent surfaces), so users get a
  diff prompt per-file as usual.
- Claude Code subagents cannot spawn other subagents (see
  `docs/harness-engineering-2026-05.md:156`), so the Developer
  cannot delegate wide searches to `explorer` directly. The `/build`
  command compensates by running an `explorer` pass from the main
  agent before invoking `developer`, and the Developer role file
  documents the hand-back path (drop a note in `scratch.md`) when
  exploration is needed mid-loop.
- The `/spec` / `/plan` / `/verify` commands now indirect through
  their subagent. Users who liked having the full behavioural
  contract inline in the command file will need to read one extra
  file to see the same content.

## Alternatives considered

- **Gate the role subagents behind a new `include_role_subagents`
  Copier question.** Rejected: the subagents are the canonical
  implementation of the slash commands the harness already ships
  unconditionally. Gating them would let a user produce a harness
  where `/spec` delegates to a `product-owner` subagent that
  doesn't exist.
- **Inline the role contracts in the command files (status quo,
  add `/build` only).** Rejected: each role's contract is non-trivial
  (output format, constraints, handoff rule) and would bloat the
  command files. Subagents exist precisely to encapsulate this.
- **Merge Product Owner and Architect into a single role.**
  Rejected: the spec → plan handoff is a natural review gate (every
  framework surveyed keeps these separate), and the artifacts are
  genuinely different (WHAT/WHY vs HOW/WHEN). Merging them would
  collapse a deliberate user-review checkpoint.
- **Adopt BMAD's full agent format verbatim** (`critical_actions`,
  `commands`, `menu`, `dependencies` blocks). Rejected: those fields
  are BMAD-specific and would not be understood by Claude Code or
  OpenCode. We borrow the *shape* (single-responsibility role,
  explicit handoff) but stay within the frontmatter both target
  tools parse.

## References

- [`template/.agents/subagents/product-owner.md`](../../template/.agents/subagents/product-owner.md)
- [`template/.agents/subagents/architect.md`](../../template/.agents/subagents/architect.md)
- [`template/.agents/subagents/developer.md`](../../template/.agents/subagents/developer.md)
- [`template/.agents/subagents/reviewer.md.jinja`](../../template/.agents/subagents/reviewer.md.jinja)
- [`template/.agents/commands/build.md.jinja`](../../template/.agents/commands/build.md.jinja)
- [ADR 0002](0002-canonicalize-commands-under-agents.md) — established
  `.agents/commands/` as the canonical source for slash commands; the
  new `/build` command lives there and is symlinked into Claude Code
  and OpenCode automatically.
- MetaGPT (arXiv 2308.00352), BMAD Method, GitHub Spec Kit, CrewAI,
  Claude Code subagents docs, OpenCode agents docs — surveyed for
  the role-based pattern.
