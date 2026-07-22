# Proposal 0001 — Adopt ICON-sc process-memory practices

**Status:** accepted (2026-07-22) — P1–P8 implemented, P9 deferred
· **Date:** 2026-07-22
**Source studied:** `grAItools/ICON-sc` (`development/` tree, `AGENTS.md`,
`CLAUDE.md`, `.claude/`, `.opencode/`, `.github/`, `tools/spec_freeze_guard.py`),
inspected at its 2026-07-21 state.

> Accepted and implemented in one pass: P1/P3/P4 →
> [ADR 0007](../decisions/0007-feature-report-and-document-liveness.md),
> P2 → [ADR 0008](../decisions/0008-decision-register-and-escalation-marker.md),
> P7 → [ADR 0009](../decisions/0009-pr-template-question.md); P5/P6/P8 are
> prose changes logged in `CHANGELOG.md`. P9 (freeze-guard hook) is deferred —
> register row `icon-sc-adoption.1` in
> [`../decisions/README.md`](../decisions/README.md). Open questions were
> resolved as recommended: register as a README section; the Developer writes
> `report.md` and the Reviewer audits it; `pr_template` defaults on. During
> review, P2's marker contract was refined from this document's sketch (a
> repo-wide "grep must only return pending" rule) to a per-diff same-PR rule
> compatible with frozen reports — ADR 0008 is authoritative.

## 1. What ICON-sc does (summary of the system inspected)

ICON-sc is a single long-running scientific project driven almost entirely by
agents. Its harness has two layers:

- A terse root `AGENTS.md` (working agreement: authority order, hard rules,
  environment) with a `CLAUDE.md` shim (`@AGENTS.md` + harness-specific tips) —
  the same shim pattern this template already generates.
- A `development/` tree that is explicitly *repo-internal process memory*,
  never published:
  - `policies/` — living, trunk-gated standing rules, one topic per file
    (workflow, naming, document kinds, verification gates, review protocol,
    reference mining, docs boundary, layout), indexed by a one-line-per-policy
    table.
  - `work/<NNNN>-<slug>/` — one folder per work unit holding a four-kind
    lifecycle: **proposal** (living until graduated) → **spec** (frozen
    contract, with a *mandatory* "Frozen interfaces" section) → **plan**
    (frozen instructions) → **report** (frozen account written at merge).
  - `ADRs/` — Nygard records, own sequence, with an explicit rule for when a
    decision deserves an ADR vs only a register row.
  - `REGISTRY.md` — one living file, two registers: the work-id allocator and
    the **trunk-decision/sign-off register** (`TD-PENDING:` marker contract).
  - `references/` — per-source reference cards plus `lock.toml`, an
    append-only provenance ledger of every consulted external source.
- Tool-layer enforcement: mirrored allow/deny permission lists in
  `.claude/settings.json` and `opencode.json`, and a stdlib-only
  `spec_freeze_guard.py` wired as both a Claude Code PreToolUse hook and an
  OpenCode plugin (one implementation, two harnesses — the same canonicalize-
  then-symlink philosophy as our ADR 0002/0004), which **fails open** and
  denies writes to frozen spec files.
- An implementer/reviewer loop: the implementer gets the full plan text; a
  **fresh** agent gets the review protocol + the plan's review checklist;
  binary verdict (`approve`/`request-changes`); merge only after approve.

## 2. Evaluation criteria

This repo is a template, so a practice is worth adopting only if it is
(a) generic across project types, (b) cheap in instruction budget (the
generated `AGENTS.md` caps at ~200 lines), (c) expressible as template files
or copier questions rather than per-project judgement, and (d) compatible with
the existing four-phase loop (`/spec` → `/plan` → `/build` → `/verify`).

## 3. Proposals

Ordered by value-for-cost. P1–P3 are the load-bearing ones.

### P1 — Add a frozen `report.md` to the feature lifecycle

**Gap.** Our lifecycle is `spec.md` → `plan.md` → `tasks.md` → (gitignored
`scratch.md`, cleared on completion). Nothing durable records what *actually
happened*: deviations from plan, negative results, follow-ups. ICON-sc's
frozen per-unit `report.md` is the memory that compounds — its reports caught
undeclared deviations, preserved measured negative results ("pytest-xdist
buys nothing on this battery — do not re-litigate blind"), and seeded every
later process improvement.

**Adopt.** Extend the spec directory to:

```
specs/<YYYY-MM>-<slug>/
├─ spec.md     # WHAT/WHY            — frozen once reviewed
├─ plan.md     # phased plan          — frozen once build starts
├─ tasks.md    # checkboxes           — living during build
├─ report.md   # what actually happened — written at GO, frozen at merge
└─ scratch.md  # working notes        — gitignored, cleared
```

Report template (kept short): *What was built* · *Deviations from plan* (each
declared, with why) · *What didn't work* (negative results, so future agents
don't retry them blind) · *Follow-ups* · *Gate result (dated)*.

**Template changes:** new `specs/.../report.md` example file; `/verify`
(reviewer GO path) instructs writing/completing `report.md` before merge;
`AGENTS.md.jinja` working-memory section updated; README tree + CHANGELOG;
ADR.

### P2 — Decision-escalation marker + lightweight decision register

**Gap.** We have ADRs but no protocol for the moment an agent hits a decision
that exceeds its authority (loosen a tolerance/assertion, add a dependency,
change an interface the spec froze). Today an agent either stops with prose or
— worse — silently resolves it. ICON-sc's best invention is making this a
*greppable contract*: any such line in a report carries the literal token
`TD-PENDING:` and gets a row in a register **in the same PR**; the register
row is later flipped to `signed-off`/`rejected` with evidence.

**Adopt (scaled down).** 

- Marker: a `DECISION-PENDING:` line in `report.md` (or the PR description)
  whenever the agent defers a decision to a human, instead of resolving it.
- Register: a generated `docs/decisions/REGISTER.md` — a single table (ID,
  date, decision, status, source, evidence). Contract:
  `grep -rn "DECISION-PENDING" specs/` must only return lines whose register
  row is still open.
- Adopt ICON-sc's ADR-vs-register rule of thumb verbatim (from its ADR-0002):
  *if the decision shapes structure and someone will later ask why, write an
  ADR and add a register row pointing at it; if it is a one-line operational
  fact (a tolerance grant, a pin), a register row alone is enough.* This goes
  in `docs/adr/README.md`.

**Template changes:** new `docs/adr/REGISTER.md` (or extend
`docs/adr/README.md` with the register section to avoid file sprawl —
maintainer's call); 3–4 lines in `AGENTS.md.jinja` (Do: "when a decision
exceeds your authority, write a `DECISION-PENDING:` line and stop");
reviewer subagent checks the grep contract; ADR.

### P3 — Authority order + "never silently resolve a contradiction"

**Gap.** When `spec.md`, `plan.md` and reality disagree, our harness gives no
rule. ICON-sc opens its `AGENTS.md` with one: *authority order on any
conflict: architecture doc > spec > plan; never silently resolve a
contradiction — record it in the report and stop if it blocks acceptance
criteria.*

**Adopt.** Two lines in `AGENTS.md.jinja` (generated form: architecture doc
(`docs/architecture.md`) > `spec.md` > `plan.md` > `tasks.md`; contradictions
are recorded in `report.md`, never silently resolved). Also restate in the
developer and reviewer subagents.

**Template changes:** `AGENTS.md.jinja`, `developer.md`, `reviewer.md.jinja`.
Prose-only; no ADR needed beyond a CHANGELOG line (or fold into P1's ADR).

### P4 — Document-liveness taxonomy

**Gap.** We never say which generated files are frozen vs living, so nothing
stops an agent from retro-editing a reviewed spec or a past ADR body.
ICON-sc's `document-kinds.md` classifies every kind (living / frozen-at-X /
append-only / dead) and precisely defines "frozen" as *content-frozen*
(mechanical path retargeting in a sanctioned migration commit is allowed).

**Adopt.** A short liveness table in `docs/harness-usage.md.jinja`:

| File | Liveness |
|---|---|
| `AGENTS.md`, `docs/*` | living |
| `spec.md` | frozen once reviewed (changes = new revision, noted in report) |
| `plan.md` | frozen once build starts |
| `tasks.md` | living during build |
| `report.md` | frozen at merge — never retro-edited; new findings go in *your* report |
| `docs/adr/NNNN-*.md` | frozen once accepted, except the Status line |
| `scratch.md` | dead on completion |

Plus one line in `AGENTS.md.jinja` pointing at it.

**Template changes:** `docs/harness-usage.md.jinja`, one `AGENTS.md.jinja`
line. Fold into P1's ADR.

### P5 — Harden the reviewer to ICON-sc's skeptical-review protocol

**Gap.** Our reviewer is already read-only, gate-running, and citation-rich —
but it trusts the developer's narrative. ICON-sc's `review-protocol.md` adds
the parts that catch real failures:

1. **Scope check first** — `git diff --stat` against the integration branch;
   every touched file must be plausibly required by the plan; touching
   another feature's spec/report or a past ADR is an automatic defect.
2. **Never trust the implementer's report** — re-run every gate, re-derive
   checkable claims (line numbers, measured values).
3. **Probe that new tests can fail** — a vacuous test (always-true assertion,
   compare-to-self, tolerance too wide to fail) is a defect, not coverage.
4. **Honesty check** — hunt *undeclared* deviations: requirements silently
   skipped, reinterpreted, or "improved". An inaccurate claim in the report
   is a defect even when the code is correct.
5. **Severity taxonomy** — findings ranked MAJOR (blocks merge) / MINOR
   (fix-or-waive) / INFO, with MAJOR definitions listed (weakened assertion,
   scope violation, undeclared deviation, false report claim…). Keep our
   GO/NEEDS-WORK verdict; NEEDS-WORK = any MAJOR.
6. Keep ICON-sc's closing line; it is exactly the right register: *"Do not
   pad the report with praise; the absence of findings is the praise."*

**Template changes:** `reviewer.md.jinja` (extend Constraints + output
format), `verify.md.jinja` (mention severity). No ADR (strengthens an
existing role); CHANGELOG.

### P6 — Gate-output reading rules

**Gap.** Our harness says "never silently skip a failing test" but nothing
about interpreting results. ICON-sc's rules are generic and cheap:

- **Passed counts may only grow.** A drop you cannot attribute line-by-line
  to your own intentional removal means stop, don't commit, report verbatim.
- **Any new skip is a finding to explain,** not to ignore.
- **Never add `-x`, `-k`, `--ignore`, or edit markers/assertions to make a
  gate pass.** If you cannot go green within scope, report honestly and stop.

**Adopt.** Add to `docs/testing.md.jinja` and the developer + reviewer
subagents (one compact bullet each). Optionally suggest (in `testing.md`
prose) keeping a baseline-count table current for large suites — the counts
themselves are per-project and not template material.

**Template changes:** `docs/testing.md.jinja`, `developer.md`,
`reviewer.md.jinja`. CHANGELOG only.

### P7 — PR template as a definition-of-done checklist

**Gap.** We generate `.github/` content only for the Copilot gate. ICON-sc
ships a `PULL_REQUEST_TEMPLATE.md` that is literally its definition of done
(spec criteria each have a passing test; frozen interfaces match; gate green;
report written; deviations declared) — cheap standing pressure on both humans
and agents.

**Adopt (opt-in).** New copier question `pr_template` (default true?)
generating `.github/PULL_REQUEST_TEMPLATE.md`: link to the feature's spec
dir; checkboxes for *gate green (`verify`)* · *each success criterion has a
test* · *report.md written, deviations declared* · *no `DECISION-PENDING:`
without a register row* · a "deviations & notes for the reviewer" free-text
section.

**Template changes:** `copier.yml` question + conditional path (note the
`.jinja`-outside-the-conditional rule), template file, README, CHANGELOG,
ADR (new question = design choice). Interaction to resolve: `.github/` is
currently created only under `copilot_code_review` — the path gating needs to
OR the two conditions or use a nested conditional segment.

### P8 — "Plans are written for a weaker agent": restate invariants inline

**Gap.** ICON-sc states it outright: *"a plan restates the invariants inline
because it is written for an agent weaker than the one that built the
slice."* Plans get executed in fresh sessions, by cheaper models, or after
compaction — a plan that depends on ambient context degrades.

**Adopt.** Instruct the architect subagent that every `plan.md` ends with a
short **Invariants** block restating the non-negotiables (gate must be green;
no test weakening; authority order; decision-escalation marker) and a
**Review checklist** section the reviewer consumes (mirroring ICON-sc's
plan → review-checklist coupling, which our `/verify` can then read).

**Template changes:** `architect.md`, `plan.md` example, `verify.md.jinja`
(read the plan's checklist). CHANGELOG.

### P9 — Freeze-guard hook (phase 2, opt-in)

**Gap.** P1/P4 declare files frozen; nothing enforces it. ICON-sc enforces
its registry invariant at the tool layer with one stdlib Python guard wired
into both Claude Code (PreToolUse hook) and OpenCode (plugin) — matching our
canonical-hooks architecture (ADR 0004) — that **fails open** so a bug can
never wedge unrelated edits.

**Adopt later, opt-in.** A generic `freeze-guard` under `.agents/hooks/`
denying Write/Edit (and narrow mutating-Bash) on: `report.md` files outside
the current feature branch's spec dir, other features' `spec.md`, and past
ADR bodies. Ship only after P1/P4 have settled, gated by a copier question;
follow ICON-sc's design points (fail open; match whole shell tokens, not
substrings; reads always allowed).

**Template changes (when taken up):** hook script + settings wiring for both
harnesses, copier question, ADR. Deliberately out of scope for the first
round — it needs careful cross-platform testing and the mergedness heuristic
is the hard part.

## 4. Considered and not adopted

- **Numeric work-ids + single-allocator `REGISTRY.md` §1 + remap tables.**
  Solves ID-collision and history-bridging for one long-lived repo with
  concurrent lanes and multiple renames. Our `<YYYY-MM>-<slug>` naming
  already avoids collisions and sorts chronologically; the allocator
  discipline would be dead weight downstream. (The *decision* half of the
  registry is adopted as P2.)
- **Reference cards + `lock.toml` provenance ledger.** Excellent for a
  porting project mining pinned upstream sources; too domain-specific for a
  generic template. Worth at most a "patterns for porting projects" aside in
  `docs/harness-usage.md` — not proposed now.
- **Verification-gate baseline tables with counts/timings.** The *reading
  rules* generalize (P6); the baselines are per-project data. `testing.md`
  can suggest the keep-current practice in one sentence.
- **`development/` consolidated tree + docs-boundary policy.** Restructuring
  our generated layout (`docs/` + `specs/`) would be breaking and buys little:
  downstream repos don't generically publish a docs site, and our layout is
  already conventional. The boundary *idea* survives in P4's liveness table.
  *Superseded 2026-07-22:* re-evaluated at the maintainer's request and
  adopted after all — see
  [proposal 0002](0002-development-tree-and-work-folder.md) and
  [ADR 0010](../decisions/0010-development-tree-and-work-folder.md), which
  weigh the brown-field collision argument this bullet undercounted.
- **Implementer/reviewer fresh-agent loop.** Already structurally present:
  our role subagents get fresh context per invocation, and `/verify` is a
  different role from `/build`. P5/P8 import the protocol content.
- **CLAUDE.md shim, kebab-case naming, mirrored permission lists.** Already
  present in the template.

## 5. Adoption for this template repo's own process (not the generated one)

Two small items apply to *this* repo directly:

- Adopt the **ADR-vs-register rule** and a tiny register section in
  `docs/decisions/README.md` (create it — the folder currently has no index),
  so one-line operational decisions stop needing full ADRs. *(Note: this
  proposal itself introduces `docs/proposals/`; if the maintainer prefers,
  future proposals can instead live as `Status: Proposed` ADRs and this
  folder stays a one-off.)*
- Use the **proposal → ADR → CHANGELOG** flow demonstrated here for future
  structural work, mirroring ICON-sc's proposal-graduation lifecycle.

## 6. Suggested phasing

| Phase | Items | Character |
|---|---|---|
| 1 | P3, P4, P5, P6, P8 | prose-only edits to existing template files; no new questions; one render-check pass |
| 2 | P1, P2 | new lifecycle file + register; touches `copier.yml`? (no — no new question needed), README, ADRs |
| 3 | P7, P9 | new copier questions + conditional paths; each needs its own ADR and render-matrix testing |

Every phase: render with multiple answer combinations per `AGENTS.md`
("Validating changes"), update `CHANGELOG.md` under `[Unreleased]`.

## 7. Open questions for the maintainer

1. **P2 register location:** separate `docs/adr/REGISTER.md` vs a section in
   `docs/adr/README.md`? (ICON-sc keeps one file for both registers; we have
   no ID allocator, so a README section may be enough.)
2. **P1 report timing:** written by the reviewer at GO, or by the developer
   before requesting `/verify` (ICON-sc: implementer writes it, reviewer
   checks its honesty)? The ICON-sc split is cleaner — recommend it.
3. **P7 default:** `pr_template` on or off by default? Recommend on; it's
   inert for non-GitHub remotes.
4. **Instruction budget:** P2+P3+P4 add ~8–10 lines to `AGENTS.md.jinja`
   (~105 → ~115 of the ~200 cap). Acceptable, or should P4's table live only
   in `harness-usage.md` with no AGENTS.md pointer?
