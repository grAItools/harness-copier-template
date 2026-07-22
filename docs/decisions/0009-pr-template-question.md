# 9. New question pr_template: a definition-of-done PULL_REQUEST_TEMPLATE.md

## Status

Accepted (2026-07-22).

## Context

The template generated `.github/` content only for the Copilot code-review
gate. ICON-sc ships a `PULL_REQUEST_TEMPLATE.md` that is literally its
definition of done — every spec acceptance criterion has a passing test, the
gate is green, the report is written, deviations are declared — which puts
cheap standing pressure on both humans and agents at the exact moment work is
declared finished. With ADRs 0007/0008 adding `report.md` and the decision
register, the harness now has enough checkable "done" criteria for such a
template to earn its place. See the proposal (item P7).

## Decision

1. **New question `pr_template`** (bool, default `true` — it is inert for
   non-GitHub remotes) generating `.github/PULL_REQUEST_TEMPLATE.md` via the
   conditional-path gate `{% if pr_template %}.github{% endif %}/`, with
   `.jinja` outside the conditional segment per the repo rule.
2. **Content:** a Feature pointer (the `specs/` directory delivered) and a
   definition-of-done checklist — gate green (rendered via `cmd('verify')`),
   success criteria evidenced, `report.md` written with deviations declared,
   no weakened tests/tolerances/assertions, every `DECISION-PENDING:` line
   registered, structural decisions ADR'd — plus a free-text "deviations &
   notes for the reviewer" section.
3. **Brown-field safety:** `.github/PULL_REQUEST_TEMPLATE.md` joins
   `_skip_if_exists`; an existing template is never overwritten.
4. **Independent of the `copilot_*` questions.** Multiple conditional
   `{% if … %}.github{% endif %}` directories coexist; Copier merges their
   rendered contents into one `.github/`.

## Consequences

- **Positive.** The definition of done is visible on every PR without costing
  `AGENTS.md` budget; checkbox drift is caught at review time.
- **Negative.** Default-`true` means brown-field repos *without* an existing
  PR template get one on `copier update` (those with one are protected by
  `_skip_if_exists`); projects not on GitHub carry a harmless extra file.
  GitHub also reads root-level and `docs/` PR templates, and `.github/`
  takes precedence — a brown-field repo keeping its template at one of those
  legacy locations gets it silently shadowed by the generated file
  (`_skip_if_exists` only protects the `.github/` path); answer
  `pr_template=false` or move the existing template into `.github/` first.
- The checklist references `report.md` and the register, so disabling those
  conventions downstream means editing the generated template by hand.

## References

- ICON-sc `.github/PULL_REQUEST_TEMPLATE.md` — the model.
- [`copier.yml`](../../copier.yml) (`pr_template`, `_skip_if_exists`),
  `template/{% if pr_template %}.github{% endif %}/PULL_REQUEST_TEMPLATE.md.jinja`.
