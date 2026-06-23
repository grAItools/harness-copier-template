# 6. Ship a comment-hygiene policy, leave enforcement to downstream

## Status

Accepted (2026-06-23).

## Context

A repo scaffolded from this template (preserf) hit a recurring problem and
fixed it in [preserf #110](https://github.com/grAItools/preserf/pull/110):
code comments and docstrings accumulated **review/release-process prose** —
internal `Slice X` / `Phase N` slice labels, `v0.x` release-scope notes, "out
of scope for this PR". These describe the *development process*, not the code.
The process moves on (the slice merges, the version bumps) but the comment
stays, so it is stale the moment it lands, and a reader can't tell which
comments describe behaviour (trust them) and which are leftover review notes
(ignore them).

The template's `docs/style.md` had no comment guidance, and nothing in the
harness surfaced the policy to a coding agent at edit time. Since this problem
is generic to any repo — not specific to preserf — the policy is worth
promoting upstream so every generated project inherits it.

preserf enforced the policy with a Python/ruff/pytest stack: ruff `ERA`
(no commented-out code) and `FIX` (no `TODO`/`FIXME`) rules in
`pyproject.toml`, plus a `tests/.../test_comment_hygiene.py` guard wired into
its verify gate. This template, by contrast, is **language- and
tooling-agnostic**: it surfaces `test`/`lint`/`verify` *commands* as questions
and ships no `pyproject.toml`, linter config, or test files. So the enforcement
mechanism does not transfer; only the policy and its agent-facing surfaces do.

## Decision

Backport the **policy and the places agents read it**, not the Python-specific
enforcement.

1. **`docs/style.md` gains a `## Comments` section** — the single source of
   truth. Four rules (explain *why* not *what*; keep comments true; no
   review/release-process prose; state a rationale once) and a worked example.
   The enforcement note is phrased generically against `{{ cmd('verify') }}`
   ("if your project wires a comment-content check or `ERA`/`FIX`-style lint
   rules into the gate…") rather than naming ruff or pytest.

2. **One-line pointers from the agent surfaces** that already read
   `docs/style.md`: an `AGENTS.md` Conventions bullet, a `developer` subagent
   constraint, and the `reviewer` subagent's implementation-quality check list.

3. **A path-scoped `.claude/rules/comments.md`** so Claude Code surfaces the
   policy exactly when editing source. Its `paths:` glob is derived from
   `primary_language`. The `copilot_code_review` `language.instructions.md`
   seed gains a matching review bullet, so the policy reaches the Copilot
   review surface too.

4. **The `primary_language` → source-glob map is extracted into a `lang_glob()`
   macro in `_macros.jinja`.** It previously lived inline in
   `language.instructions.md.jinja`; `.claude/rules/comments.md.jinja` needs the
   same map, so a shared macro keeps the two from drifting.

5. **No new copier question.** The policy is a baseline convention, included
   unconditionally (no opt-out).

6. **Enforcement tooling stays downstream.** No `pyproject.toml`, ruff config,
   or guard test is added to the template; that is the generated project's job,
   consistent with the template's language-agnostic design. We likewise do not
   add an ADR under `template/docs/adr/` — that would inject an opinionated
   decision into every downstream repo.

## Consequences

- **Positive.** Every greenfield project inherits the policy in prose plus
  three agent-read surfaces, so process prose is discouraged at authoring,
  generation, and review time. The `lang_glob()` extraction removes a
  duplicated map.
- **Negative.** Without a templated gate, the policy is advisory in generated
  repos until the user wires their own check — the template can only document
  how. `docs/style.md` is in `_skip_if_exists`, so existing (brownfield)
  projects won't get the new section on `copier update` and must add it by
  hand.
- **Revisiting.** If a future version templates language-specific linter
  config, the `ERA`/`FIX` rules and a guard could be wired into the generated
  gate then; supersede this ADR if that changes.

## References

- [preserf #110](https://github.com/grAItools/preserf/pull/110) — the source
  change this backports.
- [`template/docs/style.md.jinja`](../../template/docs/style.md.jinja) — the
  `## Comments` section.
- [`template/.claude/rules/comments.md.jinja`](../../template/.claude/rules/comments.md.jinja),
  [`_macros.jinja`](../../_macros.jinja) — the path-scoped rule and the
  `lang_glob()` macro.
