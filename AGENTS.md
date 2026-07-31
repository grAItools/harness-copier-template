# harness-copier-template — Agent Instructions

> README for AI coding agents working on **this repository**. Closest
> AGENTS.md to the file being edited wins.

This repo is a [Copier](https://copier.readthedocs.io/) **template** that
scaffolds an agent-agnostic coding harness into other repositories. It is not
an application — there is no runtime to start. "Building" it means rendering
the template and confirming the output is correct. See [`README.md`](README.md)
for the full design and provenance.

## Mental model (read this first)

- **The files under [`template/`](template/) are not this repo's files — they
  are what gets generated for downstream users.** They contain Jinja
  (`{{ ... }}`, `{% ... %}`) and most end in `.jinja`. Editing them changes
  every repo scaffolded from this template.
- **The files at the repo root** (`README.md`, this `AGENTS.md`, `copier.yml`,
  `_macros.jinja`, `hooks/`, `docs/`) are the template's *own* harness and
  machinery. They are not rendered or shipped to downstream repos.
- So: don't "fix" Jinja placeholders in `template/` as if they were bugs, and
  don't add downstream-only harness conventions (`/spec`, `/verify`, subagents)
  to *this* repo — they live inside `template/` for the generated project.

## Where things live

- [`copier.yml`](copier.yml) — questions, defaults, engine settings,
  `_skip_if_exists`, conditional-path gates.
- [`_macros.jinja`](_macros.jinja) — shared Jinja macros (e.g. `cmd`,
  `runner_file_name`). Lives at root so templates can import it regardless of
  `_subdirectory`; the file itself never renders.
- [`hooks/post_gen.py`](hooks/post_gen.py) — post-generation task: idempotent
  `.gitignore` merge + symlink creation. Stdlib-only, side-effect-light.
- [`template/`](template/) — `_subdirectory`; everything below it is rendered
  into the destination repo.
- [`docs/decisions/`](docs/decisions/) — ADRs for **this** repo (decisions of
  record). Append-only; supersede with a new file.
- [`docs/harness-engineering-2026-05.md`](docs/harness-engineering-2026-05.md)
  — the source report this template implements.

## Validating changes

Run the test suite (stdlib-only; it pins the deny/allow behaviour of
`template/.agents/hooks/block-destructive.sh`, which ships verbatim):

```sh
python3 -m unittest discover tests
```

Then render the template into a throwaway dir and inspect it:

```sh
# project_name and project_description are required (no defaults).
# Commit first and pass --vcs-ref HEAD — copier renders the latest tag
# otherwise, silently ignoring uncommitted and untagged changes:
uvx copier copy --trust --defaults --vcs-ref HEAD \
  --data project_name=Demo --data project_description="A demo" . /tmp/render-check
# vary answers to exercise gates:
uvx copier copy --trust --defaults --vcs-ref HEAD \
  --data project_name=Demo --data project_description="A demo" \
  --data task_runner=just --data copilot_code_review=true . /tmp/render-just
```

`--trust` is required because `hooks/post_gen.py` runs after generation.
Confirm: files render without leftover `{{ }}`/`{% %}`, conditional paths
appear/disappear with their gates, and the post-gen summary reports the
expected `.gitignore` block and symlinks.

## Do

- Keep `copier.yml`, `template/`, and `README.md` in sync. A new question,
  default, or generated file usually needs touches in all three.
- For a new design choice (a new question, a structural change to the layout),
  add an ADR in `docs/decisions/`.
- Render with multiple answer combinations after changing anything that's
  gated by a question.
- In `template/` docs, mark downstream fill-ins `_Fill in: …_`, inline
  placeholders bare `<name>` (never backticked, in prose as in fenced
  blocks), and durable how-this-doc-works notes as `>` blockquotes. (See
  README, "Scaffold markers in generated docs".)
- Log every user-facing change in [`CHANGELOG.md`](CHANGELOG.md) under
  `[Unreleased]`: pick the right group (`Added`/`Changed`/`Removed`), write one
  concise bullet (lead with the question/file/behaviour that changed), mark
  breaking changes `### Removed (breaking)` and add `### Upgrade notes` when a
  `copier update` needs manual action, and link the ADR if there is one. Keep
  [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + SemVer; on release,
  rename `[Unreleased]` to the version + date and add the compare link.

## Don't

- **Don't move `.jinja` inside a conditional path segment.** Copier strips the
  suffix before evaluating Jinja-in-path, so `{% if x %}foo.jinja{% endif %}`
  keeps a literal `.jinja`. Use `{% if x %}foo{% endif %}.jinja`. (See README,
  "Repository layout".)
- Don't make `hooks/post_gen.py` destructive or pull in non-stdlib deps (PyYAML
  is the only assumed import, since Copier provides it).
- Don't add a dependency or restructure the template without an ADR.
- Don't run destructive git: `push --force`, `reset --hard origin/*`, history
  rewrites on shared branches.
- Don't put secrets or per-developer paths here — use a git-ignored
  `AGENTS.local.md` / `CLAUDE.local.md`.

## Conventions

- Commit messages: **Conventional Commits 1.0.0** (e.g. `feat:`, `fix:`,
  `docs:`), imperative mood, first line ≤72 chars, no trailing period.
- Branch names: `<initials>/<slug>` for personal branches; bare slug for shared
  feature branches.
- Keep this file under ~200 lines. The instruction budget is finite; every rule
  added dilutes adherence to all the others.
