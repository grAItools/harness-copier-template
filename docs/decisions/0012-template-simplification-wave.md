# 12. Template simplification wave: fewer questions, merged role files, one hand-back convention

## Status

Accepted (2026-07-27). Partially supersedes ADR 0011 (the playbook/subagent
file split — the knowledge-grounded method content itself stays) and ADR
0005 (the separate `copilot_code_review_skill` gate — the review-rules
layout stays).

## Context

A complexity audit of the whole template surface (cost metric: instruction
budget first, then question count, concept count, duplication), followed by
an independent adversarial review of that audit, found the template had
accreted mechanism faster than value:

- 24 questions in `copier.yml`, of which 11 gated nothing worth a prompt:
  four did nothing or nearly nothing (`mode` had zero consumers,
  `project_slug` had one, `license` rendered two doc lines,
  `include_example_adr` gated the standard seed ADR), and seven gated
  things better deleted, folded, or derived.
- Every role invocation mandatorily loaded three files (subagent file +
  role playbook + `design-principles`), with verified rule duplication
  between the subagent/playbook pairs (look-it-up-before-asking,
  one-question-per-invocation, the red-flag self-review).
- Six hand-back marker tokens with per-type protocols, round-number
  carrying, and reset arithmetic ("count the `SPIKE-REQUEST:` lines below
  the last `PLAN-REVISION:` line") — performed by fresh-context agents in a
  gitignored scratch file.
- `development/harness-usage.md` (315 rendered lines) restating the
  subagent files and `AGENTS.md` nearly paragraph for paragraph, and the
  liveness/register rules appearing across seven files.
- Two verified doc defects in the `.agents/` READMEs: an authoring tip
  telling downstream users to import `_macros.jinja` (never shipped
  downstream) and a Copilot matrix row naming a nonexistent `copilot`
  question while calling `copilot-instructions.md` a redirect stub.

The review confirmed every load-bearing factual claim it checked, amended
six findings (savings arithmetic; a silent-misfire mode in the scripts
derivation for spelling variants; the Product Owner's `edit: deny` grant
conflicting with a scratch-file hand-back), and rejected none.

## Decision

Implement audit findings 1–14 as amended by the review:

1. **Questions 24 → 13.** Deleted: `mode`, `project_slug` (formatter key
   hardcoded to `project-fmt`), `license` (docs carry a `_Fill in:`
   marker), `include_example_adr` (seed ADR always ships),
   `include_example_skill` plus the `verify` skill itself,
   `include_example_spec` plus the example work unit (`development/work/`
   ships empty with a `.gitkeep`), `pr_merge_strategy` (docs carry the
   strategy-generic guidance), `cursor`, `mcp`, `copilot_code_review_skill`
   (folded into `copilot_code_review`), and `generate_scripts` — now
   **derived**: `scripts/` generates exactly when `verify_command` names
   `scripts/verify.sh` as a path. The non-equality match is the review's
   amendment — equality would silently drop the scripts for spellings
   like `bash ./scripts/verify.sh`; the implemented test is path-aware
   rather than bare substring, so `./build-scripts/verify.sh` does not
   false-positive. It lives as a never-asked (`when: false`) computed
   value in `copier.yml` because a Jinja path segment cannot contain
   `/`. Guard rails around the derivation: `scripts/verify.sh` and
   `scripts/fmt-file.sh` join `_skip_if_exists` (restoring the
   brownfield protection the deleted opt-out provided — the review's
   noted secondary loss), and a post-copy warning fires when a stale
   `generate_scripts` value supplied as data leaves the gate pointing at
   a missing script (`when: false` skips the prompt but does not reject
   provided data).
2. **Role playbooks merged into their subagent files.** Each role file
   carries its Method inline, deduplicated against its own constraints;
   `design-principles/` remains the only `.agents/skills/` entry and the
   roles keep pointing at it. This keeps ADR 0011's two placement
   constraints satisfied (no `AGENTS.md` inflation; the shared core stated
   once) while removing four files, four skill concepts, and the
   read-this-other-file-first indirection per invocation.
3. **One hand-back convention.** `SPIKE-REQUEST:`/`SPIKE-FINDING:`,
   `EXPLORER-REQUEST:`/`EXPLORER-FINDING:`, and `PLAN-REVISION:` are
   replaced by `HANDBACK(<spike|explore|replan>): …` appended to
   `scratch.md`, results appended as `RESULT(<kind>): …`, with flat
   per-kind caps: three spike hand-backs per plan, three explore
   hand-backs per phase, three replan hand-backs per feature — then the
   question goes to the user. Each role states its cap in the hand-back
   reply itself, so the bound survives description-match invocation.
   Round-number carrying and the reset arithmetic are gone. `DECISION-PENDING:` and its register contract are
   untouched. **Exception (review-caught):** the Product Owner has
   `edit: deny` and cannot append to an existing `scratch.md`; its
   clarifying-question loop stays reply-based, with a flat five-round cap.
4. **Docs shrunk.** `harness-usage.md` loses its three restatement
   sections and becomes the single home of the document-liveness table;
   the glossary-promotion rule is stated once in `glossary.md` with
   one-line references elsewhere (the reviewer still requires glossary
   edits to trace to the reviewed spec); the four `.agents/` READMEs merge
   into one (fixing both doc defects above); `tool-bootstrap.md`'s
   mise/asdf tutorial becomes a few lines linking the tools' install
   docs; `hooks/post_gen.py` drops its answers-file reader (`_read_answer`
   and the PyYAML import) for a tool-agnostic next-steps line — its
   `.gitignore` fence merge is deliberately unchanged.

## Consequences

- The default render shrinks by roughly a fifth, and per-role invocation
  load drops about 20% (one file plus one shared skill instead of two plus
  one). `copier.yml` drops from 421 to ~300 lines; the render matrix
  shrinks with every deleted boolean.
- **Breaking** for downstream repos on `copier update`: eleven answers
  disappear from `.copier-answers.yml`, the old marker tokens are gone
  from every generated surface, and previously gated files (playbooks,
  verify skill, `.cursor/`, `.mcp.*`, the example work unit) are no longer
  generated. See the CHANGELOG Upgrade notes.
- Accepted losses (the "5%"): description-match triggering of role method
  prose outside the role subagents (`design-principles` still triggers
  independently); the per-kind spike-budget reset semantics (a revised
  plan no longer earns a fresh spike budget); merge-strategy-tailored
  commit guidance; the answer-aware post-gen print; Cursor auto-attached
  context; the Copilot rules-without-skill combination (recoverable by
  deleting one file).
- **Deliberately not done — finding 15 (merge Product Owner + Architect).**
  Both the audit and the review recommend against: the WHAT/HOW wall is
  the one role separation with tool-grant enforcement behind it
  (`edit: deny` on the PO backs "the spec freezes on review"), and merging
  trades the harness's core discipline for ~100 lines.
- Two open questions the audit could not settle from repo evidence, left
  to the maintainer: **(a)** whether OpenCode is actually used downstream —
  if not, deleting the OpenCode plane (~150+ rendered lines and a concept
  plane) is the next-largest simplification; **(b)** who the template is
  for — the Copilot review seeds hardcode a numerical/HPC/ML framing that
  is right for the ICON-sc lineage but needs a fill-in framing if the
  template is meant to be general.
