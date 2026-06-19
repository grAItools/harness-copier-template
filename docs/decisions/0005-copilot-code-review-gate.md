# 5. Rework the Copilot gate around code review

## Status

Accepted (2026-06-05).

## Context

The template generated `.github/copilot-instructions.md` as a one-line
redirect to `AGENTS.md`, gated on a question named `copilot`:

```
This repository's canonical agent instructions live in `AGENTS.md` …
See ../AGENTS.md.
```

The assumption was that GitHub Copilot reads `AGENTS.md` directly, so a
thin pointer was enough. That assumption does not hold for Copilot **code
review**, which is the surface most users actually care about:

- Copilot code review reads only the files under `.github/`, from the
  pull request's **base** branch, capped at **4,000 characters per file**.
- It does **not** read `AGENTS.md` (confirmed by GitHub docs and community
  discussion #174058), and it does **not** follow deep import chains.

So the redirect propagated nothing: every review ran with zero
project-specific guidance. The `copilot` question name also implied a
broader scope ("set up Copilot") than the feature delivers.

Separately, the seed rules were written for web-app code (SQL injection,
request handlers, IDOR), which is a poor default for this template's
audience (scientific computing / HPC / ML), where the high-value review
concerns are numerical stability, reproducibility, precision/dtype,
vectorization, GPU/MPI resource use, and unsafe deserialization of model
checkpoints.

## Decision

Rework the gate so the review rules live where Copilot code review reads
them, and scope the question name to what it configures.

1. **Rename `copilot` → `copilot_code_review`** *(breaking)*. The name now
   matches the surface it configures. Existing repos rename the key in
   `.copier-answers.yml` before `copier update` (see the CHANGELOG
   *Upgrade notes*).

2. **Populate `.github/copilot-instructions.md`** with review-targeted
   rules (`Always flag` / `Don't comment on` / `Review style`), referencing
   the project's real `fmt`/`lint` commands via the `cmd()` macro. Kept
   under the 4,000-char cap (target ≤ 3,500).

3. **Add gated `.github/instructions/`** path-scoped rules:
   - `language.instructions.md` — `applyTo:` glob derived from
     `primary_language`. The glob table falls back to `**/*` for any
     language without a specific mapping, so adding a future
     `primary_language` choice cannot hard-fail the render.
   - `security.instructions.md` — `applyTo: "**"` with
     `excludeAgent: "coding-agent"` so the rules shape review without
     steering the coding agent's generation.

4. **Add a separate `copilot_code_review_skill` gate** (off by default —
   GitHub agent skills for code review are a public preview) generating
   `.github/skills/code-review/SKILL.md`. It is independent of
   `copilot_code_review`; a copy-time note warns when the skill is enabled
   without the accompanying review rules.

5. **Retarget the seed rules** at correctness-critical numerical / data /
   compute code, retaining web/service-security rules but scoping them to
   service code. Add `fortran` and `julia` to `primary_language` (and
   extend the `cpp` glob to cover CUDA) so the language-scoped rules apply
   to this template's audience.

Both `.github/` subtrees are gated independently via two
`{% if … %}.github{% endif %}` directory segments that Copier unions into a
single `.github/`, matching the existing `{% if cursor %}.cursor{% endif %}`
pattern.

## Consequences

**Positive.**

- Copilot code review now receives the project's actual conventions
  instead of a redirect it never followed. Rules live in `.github/`, within
  the per-file cap, restated rather than imported (Copilot code review
  follows neither `AGENTS.md` nor import chains).
- Path-scoped rules let language and security concerns apply only where
  relevant, and `excludeAgent: "coding-agent"` keeps security guidance out
  of code generation.
- The question name communicates scope honestly, and the skill is gated
  separately so the stable review config is not coupled to a preview
  feature.
- Defaults match the template's audience (numerical / HPC / ML), with the
  language-glob table falling back gracefully for unmapped languages.

**Negative.**

- Breaking rename: existing repos must edit `.copier-answers.yml` before
  `copier update`, or the answer is dropped and the feature silently turns
  off (documented in *Upgrade notes*).
- The review prose is necessarily duplicated across
  `copilot-instructions.md`, `instructions/*.instructions.md`, and
  `skills/code-review/SKILL.md` because Copilot code review cannot follow
  imports. The copies can drift; they are seed defaults the user is
  expected to trim, so a shared-macro source was judged not worth the
  indirection (see Alternatives).
- Command defaults for `fortran`/`julia` fall through to the generic
  `other` arm (TODO placeholders) to be filled in after generation.

## Alternatives considered

- **Keep the `AGENTS.md` redirect.** Rejected: Copilot code review does
  not read `AGENTS.md`, so the redirect guarantees zero review guidance.
- **Emit the shared review prose from a `_macros.jinja` block** to avoid
  duplication across the four files. Rejected for now: the files are seed
  defaults meant to be trimmed per project, the duplication is by design
  (no import-following), and a macro would add indirection without removing
  the underlying need for each file to be self-contained. Revisit if the
  seeds grow enough that drift becomes a real maintenance cost.
- **Fold the skill into `copilot_code_review`.** Rejected: agent skills
  for code review are a public preview; coupling the stable instructions
  config to a preview feature would force preview opt-in on users who only
  want the review rules.
- **Hard-validate `copilot_code_review_skill` requires `copilot_code_review`.**
  Rejected: the skill works standalone, so a copy-time note is the right
  altitude — a validator would block a legitimate config.

## References

- [`copier.yml`](../../copier.yml) — `copilot_code_review`,
  `copilot_code_review_skill`, and the `primary_language` choices.
- [`template/{% if copilot_code_review %}.github{% endif %}/copilot-instructions.md.jinja`](../../template/%7B%25%20if%20copilot_code_review%20%25%7D.github%7B%25%20endif%20%25%7D/copilot-instructions.md.jinja)
- [`template/{% if copilot_code_review %}.github{% endif %}/instructions/`](../../template/%7B%25%20if%20copilot_code_review%20%25%7D.github%7B%25%20endif%20%25%7D/instructions/)
  — `language.instructions.md.jinja`, `security.instructions.md.jinja`.
- [`template/{% if copilot_code_review_skill %}.github{% endif %}/skills/code-review/SKILL.md.jinja`](../../template/%7B%25%20if%20copilot_code_review_skill%20%25%7D.github%7B%25%20endif%20%25%7D/skills/code-review/SKILL.md.jinja)
- GitHub Copilot code review docs and community discussion #174058 —
  behaviour of `.github/` instruction loading (base branch, 4,000-char
  cap, no `AGENTS.md`, no import chains).
