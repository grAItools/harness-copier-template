# 7. Add a frozen per-feature report.md, an authority order, and a document-liveness taxonomy

## Status

Accepted (2026-07-22).

## Context

The generated harness's working memory ended at `tasks.md` plus a gitignored
`scratch.md` that is cleared on completion. Nothing durable recorded what
*actually happened* during a feature: deviations from the plan, approaches
tried and abandoned, follow-ups. Each feature's process knowledge evaporated
at merge.

The ICON-sc project (same organization) runs an agent-driven workflow whose
per-work-unit `report.md` — frozen at merge, never retro-edited — proved to be
the memory that compounds: reports caught undeclared deviations at review
time, preserved measured negative results so later agents did not re-attempt
them, and seeded process improvements. ICON-sc also states an explicit
authority order for document conflicts (architecture > spec > plan, "never
silently resolve a contradiction — record it and stop") and classifies every
document kind by liveness (living / frozen-at-X / append-only / dead), which
is what makes "frozen" enforceable as a review criterion. See
[`docs/proposals/0001-adopt-icon-sc-process-memory-practices.md`](../proposals/0001-adopt-icon-sc-process-memory-practices.md)
(items P1, P3, P4) for the full evaluation.

## Decision

1. **The spec directory gains `report.md`** — written by the Developer as the
   work happens (deviations and dead ends recorded when they occur), completed
   before the final `/verify`, audited for honesty by the Reviewer, frozen at
   merge. Sections: What was built · Deviations from plan · What didn't work ·
   Decisions escalated · Follow-ups · Gate. The example file ships with the
   `include_example_spec` directory; the layout is documented in `AGENTS.md`
   regardless of that answer, like the rest of the spec-directory layout.
2. **`AGENTS.md` states the authority order** — `development/architecture.md` >
   `spec.md` > `plan.md` > `tasks.md` — and the rule that contradictions are
   recorded in `report.md`, never silently resolved. Restated in the
   `developer` subagent (as a working rule) and the `reviewer` subagent (as
   the standard for judging plan conformance).
3. **`development/harness-usage.md` gains a Document liveness table** (which files
   are living, when each freezes, `report.md` never retro-edited, ADR bodies
   frozen once accepted). `AGENTS.md` carries a three-line summary and links
   to it.
4. **No new copier question.** The report is part of the baseline loop; a
   project that skips the loop for small fixes (already sanctioned) simply has
   no report for those changes.

## Consequences

- **Positive.** Feature history becomes greppable and durable; the Reviewer
  gets a fourth concrete axis (report honesty, ADR 0008 wires the checks);
  "frozen" is now a defined term the reviewer can flag violations of.
- **Negative.** One more file per feature to keep current; agents that
  reconstruct the report at the end (instead of logging as they go) may write
  sanitized history — the Developer instructions call this out explicitly.
- **Enforcement is by instruction and review, not tooling.** A freeze-guard
  hook (ICON-sc has one) was evaluated and deferred — see proposal item P9.

## References

- ICON-sc `development/` tree: `work/<NNNN>-<slug>/report.md`,
  `policies/document-kinds.md`, `AGENTS.md` (authority order).
- [`template/development/work/…/report.md`](../../template/development/work/%7B%25%20if%20include_example_spec%20%25%7DYYYY-MM-example%7B%25%20endif%20%25%7D/report.md),
  [`template/AGENTS.md.jinja`](../../template/AGENTS.md.jinja),
  [`template/development/harness-usage.md.jinja`](../../template/development/harness-usage.md.jinja).
