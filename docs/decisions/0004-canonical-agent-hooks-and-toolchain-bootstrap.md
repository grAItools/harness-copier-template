# 4. Canonical agent hooks and toolchain bootstrap

## Status

Accepted (2026-06-18).

## Context

The harness wires Claude Code and OpenCode to a shared set of `.agents/`
definitions. Four gaps in that wiring motivated this change:

- The destructive-command deny-list was an inline `grep` inside
  `.claude/settings.json` — not reusable as a single definition that other
  surfaces (or CI, or another agent) can share.
- There was no automated build-tool bootstrap: a fresh session, sandbox, or
  Claude Code on the web that lacked the package manager simply failed at the
  verify gate.
- OpenCode had no auto-format, while Claude Code formatted on edit via its
  `PostToolUse` hook — an avoidable asymmetry.
- The two permission surfaces had drifted (`.claude` allowed read-only
  `ls`/`cat`/`head`/`tail`; `.opencode` did not), and there was no written
  record of which agents the harness supports or how to add one.

Any fix must stay package-manager-agnostic: this template targets `uv`, `pixi`,
`cmake`, and `other`, so behaviour has to flow through the existing `cmd()` macro
(`_macros.jinja`), the `package_manager` / `task_runner` / `generate_scripts`
answers, and the `include_claude_hooks` gate — never hard-coded to one manager.

## Decision

Add a canonical `template/.agents/hooks/` directory and wire both tool surfaces
to it, generalized across package managers:

- **`block-destructive.sh`** (always generated, mode `0755`) — the single source
  of truth for the destructive-command deny-list. The Claude Code
  `PreToolUse(Bash)` hook pipes the candidate command through it; the OpenCode
  `permission.bash` deny globs remain a hand-kept, weaker (prefix-only) mirror,
  documented as such (OpenCode cannot call a script). The Claude hook guards the
  call **fail-closed** (`[ -r "$S" ] || exit 2`) so a missing matcher blocks
  rather than silently failing open.
- **`ensure-toolchain.sh`** — an idempotent build-tool bootstrap, generated
  **only for `uv` and `pixi`** (the package managers with a one-line installer),
  via the empty-filename conditional path
  `{% if package_manager in ['uv','pixi'] %}ensure-toolchain.sh{% endif %}.jinja`.
  It is wired into the Claude Code `SessionStart` hook (`|| true`, so an offline
  install failure is quiet) and the `Stop` hook self-heals through it before
  running the gate. For `cmake`/`other` no script is produced and the hooks fall
  back to running the gate directly.
- **OpenCode native `formatter`** (when `generate_scripts=true`) routes edits
  through the same per-file entry point Claude Code uses (`scripts/fmt-file.sh`)
  and disables the conflicting OpenCode built-in per `primary_language` (e.g.
  `ruff`, `prettier`, `gofmt`, `rustfmt`, `clang-format`); languages OpenCode
  ships no built-in for (Java, C#) get the custom formatter with nothing to
  disable, and `other` gets a commented stub.
- **`template/.agents/README.md`** records the single-source-of-truth principle
  and a supported-agents matrix (Claude Code, OpenCode, Copilot, OpenAI Codex,
  Google Gemini CLI, and natively-`AGENTS.md` agents) plus a recipe for adding an
  agent. **`template/docs/harness-usage.md`** is a unified driving guide
  (added to `_skip_if_exists`).
- **Permission posture:** `ls/cat/head/tail` are added to the OpenCode allow-list
  to match `.claude`, but `find` is dropped from **both** surfaces because
  `find -delete` / `-exec rm` bypasses the deny-list.
- The single-package-manager bin directory is centralized in a
  `toolchain_bin_dir()` macro in `_macros.jinja`, imported by both
  `ensure-toolchain.sh.jinja` and the Stop-hook `PATH` export so they cannot
  drift.
- The stray `"hooks"` entry is removed from `copier.yml`'s `_exclude`: it was a
  redundant leftover (the template's own `hooks/` lives outside `_subdirectory`)
  that matched — and silently dropped — the new `template/.agents/hooks/`.

Three scoping decisions were confirmed with the template owner:

1. **Bootstrap only for known installers** (`uv`/`pixi`); `cmake`/`other` get no
   bootstrap script.
2. **Codex/Gemini are documentation-only** — recorded in `.agents/README.md`, no
   new Copier question and no `.gemini/` config file shipped.
3. **The single-source-of-truth principle is documented in `.agents/README.md`,
   not as a numbered ADR shipped inside `template/`** — ADR numbering belongs to
   each generated repo, so the template states the principle as prose instead.

## Consequences

**Positive.**

- One deny-list definition, consumed by Claude Code directly and mirrored (with a
  documented weaker-glob caveat) by OpenCode. Fail-closed behavior removes the
  shell-dependent fail-open/fail-shut hazard of calling a possibly-missing script.
- `uv`/`pixi` projects bootstrap their build tool automatically at session start
  and self-heal at the verify gate, including Claude Code on the web.
- OpenCode reaches feature parity with Claude Code's auto-format without
  double-formatting.
- The two permission surfaces no longer drift, and `find`'s destructive forms are
  no longer auto-allowed.

**Negative.**

- The default harness ships two more files under `.agents/` and a new directory.
  `block-destructive.sh` greps the whole Bash tool-input blob, so benign
  read-only commands containing a forbidden substring (e.g. `grep 'DROP TABLE'`)
  are conservatively blocked — pre-existing behavior, now canonical. A future
  follow-up could extract just the command before matching.
- `docs/tool-bootstrap.md` and `docs/harness-usage.md` are in `_skip_if_exists`,
  so brownfield repos must merge the `ensure-toolchain.sh` reference by hand
  (noted under CHANGELOG "Upgrade notes").

## Alternatives considered

- **Generalize the bootstrap to every package manager.** Rejected: `cmake` and
  `other` have no canonical one-line installer, so an auto-bootstrap would be a
  guess; decision 1.
- **Add a Copier `gemini` toggle / ship `.gemini/settings.json`.** Rejected as
  scope creep; Codex reads `AGENTS.md` natively and Gemini needs only a one-file
  stub the matrix documents; decision 2.
- **Ship a numbered single-source-of-truth ADR inside `template/`.** Rejected:
  ADR numbers are per-generated-repo; the principle lives in `.agents/README.md`
  instead; decision 3.
- **Keep the inline `grep` deny-list in `.claude/settings.json`.** Rejected: it
  could not be shared as a single source of truth across surfaces — the whole
  point of factoring it into a script.

## References

- [`template/.agents/hooks/block-destructive.sh`](../../template/.agents/hooks/block-destructive.sh)
- `template/.agents/hooks/{% if package_manager in ['uv', 'pixi'] %}ensure-toolchain.sh{% endif %}.jinja`
- [`template/.agents/README.md`](../../template/.agents/README.md)
- [`template/docs/harness-usage.md.jinja`](../../template/docs/harness-usage.md.jinja)
- [`_macros.jinja`](../../_macros.jinja) — `toolchain_bin_dir()`
