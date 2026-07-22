# Decisions of record

Nygard-format ADRs, `NNNN-<kebab-title>.md`, zero-padded, append-only.
Supersede with a new file; never edit an accepted ADR's body (the Status line
may change). Structural proposals are drafted in [`../proposals/`](../proposals/)
first and graduate to ADRs here on acceptance.

| # | Title | Status |
|---|---|---|
| [0001](0001-decouple-task-runner-and-scripts.md) | Decouple task runner and scripts | accepted |
| [0002](0002-canonicalize-commands-under-agents.md) | Canonicalize commands under `.agents/` | accepted |
| [0003](0003-role-based-subagents-and-build-command.md) | Role-based subagents and `/build` command | accepted |
| [0004](0004-canonical-agent-hooks-and-toolchain-bootstrap.md) | Canonical agent hooks and toolchain bootstrap | accepted |
| [0005](0005-copilot-code-review-gate.md) | Copilot code-review gate | accepted |
| [0006](0006-comment-hygiene-policy.md) | Comment-hygiene policy, enforcement downstream | accepted |
| [0007](0007-feature-report-and-document-liveness.md) | Feature `report.md`, authority order, document liveness | accepted |
| [0008](0008-decision-register-and-escalation-marker.md) | Decision register and `DECISION-PENDING:` marker | accepted |
| [0009](0009-pr-template-question.md) | `pr_template` question (definition-of-done PR template) | accepted |

**ADR or register row?** If the decision shapes structure — of the template,
its questions, or the generated layout — and someone will later ask *why*,
write an ADR and add a register row whose Source points at it. If it is a
one-line operational fact, a register row alone is enough.

## Decision register

One row per escalated or granted decision (see ADR 0008; this repo uses the
same convention it generates). Rows are appended and their Status flipped in
place (`pending` → `accepted` / `rejected`); nothing else is edited.

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| icon-sc-adoption.1 | 2026-07-22 | Defer the freeze-guard hook (proposal item P9) until the report/liveness conventions settle | accepted | [proposal 0001](../proposals/0001-adopt-icon-sc-process-memory-practices.md) §3 P9 | — |
