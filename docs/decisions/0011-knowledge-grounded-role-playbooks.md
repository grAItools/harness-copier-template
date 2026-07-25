# 11. Knowledge-grounded role playbooks, design-principles skill, and glossary

## Status

Accepted (2026-07-25).

## Context

ADR 0003 gave the harness role-scoped subagents (Product Owner, Architect,
Developer, Reviewer) with artifact handoffs and tool allowlists. Those files
define each role's *process* — what it produces, where it stops, what it may
touch — but say almost nothing about its *method*: how a Product Owner
actually reaches shared understanding, how an Architect chooses between
designs or de-risks an assumption, what "implementation quality" concretely
means to a Reviewer beyond comment hygiene and vacuous-test probes.

That method knowledge exists and is stable. Four sources cover it with
strong overlap: Ousterhout's *A Philosophy of Software Design* (complexity,
deep modules, errors defined out of existence, comments as design), Hunt &
Thomas's *The Pragmatic Programmer* (DRY, orthogonality, contracts,
tracer bullets, testing discipline), Evans's *Domain-Driven Design*
(ubiquitous language, model/code binding), and Brooks's *The Design of
Design* (iterative goal discovery, explicit user models and constraints,
design rationale capture, exemplars).

Two placement constraints ruled the design:

- `AGENTS.md` has a hard instruction budget (~200 lines; every added rule
  dilutes the rest), so the method content cannot live there.
- Subagent files are loaded whole on every invocation; inflating each with
  a full design curriculum taxes every run and duplicates the shared core
  four times, violating the single-source rule the harness itself preaches.

Skills already solve exactly this: on-demand, per-topic instruction files
shared across Claude Code and OpenCode via the existing symlinks.

## Decision

1. **Five ungated skills** under `.agents/skills/`:
   - `design-principles/` — the shared core: prime directives, module and
     interface rules, domain/naming rules, construction rules, and a
     red-flag checklist, each tagged with its source book.
   - `product-owner-playbook/`, `architect-playbook/`,
     `developer-playbook/`, `reviewer-playbook/` — one method file per
     role, citing the shared core instead of restating it.
2. **Subagents point at their playbook** ("read it before starting; it is
   part of your instructions") and stay lean; the Reviewer's playbook
   explicitly may not override the verdict/gate rules in the subagent file.
3. **`development/glossary.md`** joins the generated tree (and
   `_skip_if_exists`): the project's ubiquitous language. Specs gain a
   `## Glossary` section; the `/spec` wrap-up promotes reviewed terms
   (the PO subagent cannot write outside the feature directory);
   `AGENTS.md` and `development/README.md` link it.
4. **Plan-phase de-risking**: the Architect must sketch two decompositions
   (the `Architecture decisions` block gains a `Considered:` line) and may
   request **spikes** — the `/plan` command instructs the main agent to run
   the throwaway experiment and hand findings back via `scratch.md`,
   because the architect subagent has no bash. Plans gain an optional
   `## Spike findings` section; spec-contradicting findings go back to the
   Product Owner. Phase 1 defaults to a tracer bullet when the feature
   spans layers.
5. **Spec format** gains `## Constraints` (with the budgeted resource) and
   `## Glossary`; the Product Owner's single-clarifying-question rule
   becomes an explicit protocol: explore the repo first, then one question
   per turn with a recommended answer, until the user confirms shared
   understanding.

The playbooks are ungated (no new question), like the subagents they serve:
they are the roles' method, not an optional example.

## Consequences

- Roles act on a written, sourced method instead of whatever design taste
  the underlying model happens to have; the shared core lives in one file,
  so tightening a rule tightens all four roles at once.
- Skill content loads only when a role starts work — `AGENTS.md` stays
  within budget and non-role sessions pay nothing.
- The books' guidance is vendored as a distillation, not referenced: the
  skills work in any generated repo with no external knowledge base. The
  cost is that improving the distillation means editing this template —
  accepted, since downstream repos must be self-contained.
- Downstream repos that already customised their subagent files will get
  Copier's overwrite prompt on update and can merge the playbook pointer
  manually.
- Brown-field repos keep their existing `development/glossary.md` if one
  exists (`_skip_if_exists`).
- Alternative considered — gating the playbooks behind an
  `include_role_playbooks` question: rejected; a role without its method
  reverts to exactly the under-specified behaviour this ADR removes, and
  opt-outs can delete the directories.
