# 8. Decision register and the DECISION-PENDING escalation marker

## Status

Accepted (2026-07-22).

## Context

The generated harness had ADRs but no protocol for the moment an agent hits a
decision that exceeds its authority — loosening a test tolerance or assertion,
adding a dependency, changing behaviour the spec froze. An agent either
stopped with unstructured prose or silently resolved the question, and there
was no ledger of small operational decisions (a granted tolerance, a pin)
that don't warrant a full ADR.

ICON-sc solves this with a greppable contract: any such line in a report
carries the literal token `TD-PENDING:` and gets a row in a decision register
*in the same PR*; the row's Status is later flipped (`signed-off` /
`rejected`) with evidence. Its ADR-0002 records why the register and the ADRs
stay two instruments: the register answers "what is pending and who signed
off", the ADRs answer "why is it this way"; architecture-shaped decisions get
both. See the proposal (item P2) for the evaluation.

## Decision

1. **Marker:** an agent that hits an out-of-authority decision writes a
   `DECISION-PENDING:` line in the feature's `report.md` and stops. Stated in
   `AGENTS.md`, the `developer` subagent, and `development/harness-usage.md`.
2. **Register:** a `## Decision register` section in the generated
   `development/adr/README.md` (a section, not a new file — the template has no ID
   allocator and the ADR index is already the natural home). One row per
   decision: ID (`<feature-slug>.<k>`), date, decision, status
   (`pending` → `accepted`/`rejected`), source, evidence. Rows are appended
   and Status flipped in place; nothing else is edited.
3. **Contract:** every `DECISION-PENDING:` line (the colon form is the
   marker; colon-less mentions are prose) lands in the same PR as its
   register row. The `reviewer` subagent checks the contract per diff —
   a marker line added without a row is a MAJOR defect. Because reports
   freeze at merge, marker lines in merged reports stay as history and the
   register alone records outcomes: "what is still open" is answered by
   scanning the register for `pending` rows, never by grepping reports.
4. **ADR-vs-register rule** (adopted from ICON-sc ADR-0002 nearly verbatim):
   structure-shaping decisions get an ADR plus a register row pointing at it;
   one-line operational facts get a row alone.

## Consequences

- **Positive.** Escalation becomes cheap and auditable; "what is pending" is
  one grep; small decisions stop being invisible or bloating the ADR series.
- **Negative.** The register is one more surface that can drift if humans
  resolve decisions out-of-band; the reviewer's check only sees the diff, so
  markers written elsewhere (PR descriptions) rely on the PR-template
  checkbox (ADR 0009). The generated `development/adr/README.md` now accumulates
  downstream rows, so it joins `_skip_if_exists` — a brown-field re-copy
  never overwrites a populated register (at the cost that register-section
  wording improvements reach existing repos only via `copier update`'s
  three-way merge or by hand).
- This repo's own `docs/decisions/README.md` adopts the same register and
  rule, so the template practises what it generates.

## References

- ICON-sc `development/REGISTRY.md` §3, `ADRs/0002-decision-register-and-adrs.md`,
  `policies/naming-conventions.md` (the `TD-PENDING:` contract).
- [`template/development/adr/README.md`](../../template/development/adr/README.md),
  [`template/.agents/subagents/reviewer.md.jinja`](../../template/.agents/subagents/reviewer.md.jinja).
