# Proposal 0002 — development/ tree, work/ folder, and the policies/ question

**Status:** accepted (2026-07-22) — items 1–2 adopted (bundled into the same
release as proposal 0001 to avoid a second downstream migration), item 3
resolved as "rules, not folder" · **Date:** 2026-07-22
**Decision of record:** [ADR 0010](../decisions/0010-development-tree-and-work-folder.md).

Maintainer-suggested follow-up to
[proposal 0001](0001-adopt-icon-sc-process-memory-practices.md): adopt more of
ICON-sc's tree structure. Three suggestions, evaluated against the same
criteria (generic value, instruction-budget cost, expressible as template
mechanics, compatible with the four-phase loop).

## 1. Rename the generated `docs/` to `development/` — ADOPT

ICON-sc's ADR-0000 records the driving constraint — "`docs/` must stay a pure
Sphinx site source" — and rejected `docs/development/` nesting for blurring
the published/internal boundary. For this template the argument is stronger:

- **Brown-field collisions are the template's core use case.** Existing repos
  have real user docs in `docs/`; `_skip_if_exists` then silently blocks
  harness files (and `AGENTS.md` links point at files without the referenced
  anchors). A dedicated tree removes the collision class.
- **Publishing hazard:** `docs/` is auto-consumed by GitHub Pages / Read the
  Docs / MkDocs defaults; the decision register and agent manuals must not
  land on a published site.
- **Org consistency** with ICON-sc's vocabulary.

Costs, accepted knowingly: a breaking migration for existing generated repos
(`git mv` recipe in the CHANGELOG Upgrade notes), wide-but-mechanical
cross-reference churn (including the `.opencode` `instructions` array), and
`development/` being less conventional than `docs/`. Judgment call recorded:
the generated `architecture.md` is agent orientation and moves to
`development/` — unlike ICON-sc, whose architecture doc is published. `docs/`
itself is simply no longer generated (like `src/`, it is the project's own).

## 2. Rename `specs/` to `work/` — ADOPT, nested as `development/work/`

Premise correction: `specs/` was a top-level sibling of `docs/`, not inside
it. The rename stands regardless — since `report.md` joined the lifecycle
(ADR 0007), "specs" names one file kind of five; ICON-sc converged on
`work/<id>-<slug>/` for the same reason (ADR-0006, TD-54.1). Nesting under
`development/` keeps one process-memory tree, one boundary, one `.gitignore`
prefix, at the cost of longer paths. Bundled with item 1 so downstream repos
migrate once, not twice.

## 3. `policies/` folder — DO NOT ADOPT the folder; adopt its two rules

ICON-sc's rationale (ADR-0000, `policies/README.md`): a home for **living,
trunk-gated standing rules**, distinct from frozen ADRs (reasoning) and frozen
work documents, with the edit protocol "agents follow them and propose changes
via a proposal or register row — never by silently editing during a work
unit." The template already has a distributed policy layer in the surfaces
agents actually read:

| ICON-sc policy | Template equivalent |
|---|---|
| `agent-workflow.md` | the four commands + `harness-usage.md` |
| `review-protocol.md` | the `reviewer` subagent definition |
| `verification-gates.md` | `testing.md` (incl. gate-reading rules) |
| `document-kinds.md` | the Document liveness table |
| `naming-conventions.md` | `AGENTS.md` Conventions + `adr/README.md` |
| `docs-boundary.md` | `development/README.md` boundary paragraph |

A parallel `policies/` tree would duplicate these (drift) or hollow them out
(an extra read hop per subagent invocation). ICON-sc needs the folder because
its policies are bespoke project content; the template's policies *are* the
shipped harness. Adopted instead: the **one-line index README** for the tree
and the **trunk-gated rule** (in `development/README.md` and the liveness
table). Register row for the folder rejection: `icon-sc-adoption.2` in
[`../decisions/README.md`](../decisions/README.md).
