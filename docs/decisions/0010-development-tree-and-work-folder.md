# 10. Consolidate generated process memory under development/; rename specs/ to work/; no policies/ folder

## Status

Accepted (2026-07-22).

## Context

The generated harness spread its process memory across two top-level trees:
`docs/` (architecture, style, testing, tool-bootstrap, harness-usage, `adr/`)
and `specs/` (per-feature lifecycle). Three problems, sharpened by ADRs
0007–0009:

1. **Brown-field collisions.** Repos adopting the harness often already have a
   `docs/` full of real user documentation. `_skip_if_exists` protection cuts
   both ways there: an existing `docs/style.md` silently blocks the harness
   style guide, and `AGENTS.md` then links to a file lacking the anchors the
   harness references.
2. **Publishing hazard.** `docs/` is auto-consumed by GitHub Pages, Read the
   Docs, and MkDocs/Docusaurus defaults; harness internals (the decision
   register, agent manuals) do not belong on a published site. ICON-sc's
   ADR-0000 states the constraint that drove its own reorganization —
   "`docs/` must stay a pure Sphinx site source" — and rejected
   `docs/development/` nesting because it "blurs the published/internal
   boundary".
3. **A stale name.** Since ADR 0007 the `specs/` folder holds
   `spec.md`/`plan.md`/`tasks.md`/`report.md`/`scratch.md` — "specs" names one
   file kind of five. ICON-sc hit the same drift and converged on
   `work/<id>-<slug>/` per-unit folders (its ADR-0006/TD-54.1).

The evaluation, including the `policies/` question:
[`docs/proposals/0002-development-tree-and-work-folder.md`](../proposals/0002-development-tree-and-work-folder.md).

## Decision

1. **All generated process memory moves to one top-level `development/`
   tree:** `development/{architecture,style,testing,tool-bootstrap,harness-usage}.md`,
   `development/adr/` (ADRs + decision register), and
   `development/work/<YYYY-MM>-<slug>/` (the per-feature lifecycle, formerly
   `specs/`). Branch/date-slug naming is unchanged.
2. **`docs/` is no longer generated.** It stays reserved for the project's own
   user documentation, the way `src/` is for sources. The boundary rule (from
   ICON-sc's docs-boundary policy): `development/` is repo-internal, never
   published, never linked from a documentation site; development content
   wanted user-facing is rewritten under `docs/`, not moved or linked.
3. **A new always-generated `development/README.md`** indexes the tree one
   line per entry, states the boundary, and carries the trunk-gated rule:
   these documents are living but changed via a dedicated PR or a
   decision-register row — never silently edited mid-feature. The Document
   liveness table's `development/*.md` row states the same rule.
4. **No `policies/` folder.** ICON-sc's rationale for one — a home for living
   standing rules, distinct from frozen records, with a trunk-gated edit
   protocol — is already satisfied here: the harness's standing rules live in
   the surfaces agents actually read (`AGENTS.md`, the subagent definitions,
   the commands, `development/*.md`). A parallel `policies/` tree would
   duplicate them (drift) or hollow them out (an extra read hop per subagent
   invocation). What transfers is the index (item 3) and the trunk-gated rule,
   not the folder.
5. **Brown-field protection follows the files:** the `_skip_if_exists` entries
   move to their `development/` paths; `development/README.md` is not skipped
   (it is pure index, safe to refresh).

## Consequences

- **Positive.** One tree to explain and to gitignore-scope; no collision with
  downstream user docs; no accidental publication; org-level consistency with
  ICON-sc's vocabulary; `work/` names what the folder holds.
- **Negative (breaking).** Existing generated repos must `git mv` the harness
  files before `copier update`, or Copier re-creates them at the new paths
  alongside the old ones — recipe in `CHANGELOG.md` Upgrade notes. The stale
  `specs/*/scratch.md` gitignore line must be removed by hand (the post-gen
  hook appends, never removes). `development/` is less conventional than
  `docs/` — the cost of the boundary.
- **Deliberate divergence from ICON-sc:** its architecture doc is published
  and lives in `docs/`; our generated `architecture.md` is agent orientation
  and lives in `development/`. A project that grows a real published
  architecture doc writes it under its own `docs/` and may point `AGENTS.md`
  at it.

## References

- ICON-sc `development/ADRs/0000-development-tree-reorganization.md`,
  `development/policies/docs-boundary.md`, `development/policies/README.md`.
- [`docs/proposals/0002-development-tree-and-work-folder.md`](../proposals/0002-development-tree-and-work-folder.md).
- [`copier.yml`](../../copier.yml) (`_skip_if_exists`),
  [`template/development/README.md`](../../template/development/README.md).
