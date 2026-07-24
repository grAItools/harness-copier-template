#!/usr/bin/env python3
"""
Post-generation copier task.

Runs in the *destination* directory after all template files are rendered.

Responsibilities
----------------
1. Idempotently append agent-harness entries to an existing .gitignore that
   _skip_if_exists preserved. We never duplicate lines; we append only what's
   missing, between fenced markers, so a subsequent `copier update` keeps the
   block tidy.
2. Create the .claude/{skills,agents,commands} and .opencode/{skills,agents,commands}
   symlinks that point at the canonical .agents/{skills,subagents,commands} sources.
   We create them as relative symlinks when the platform supports them, and emit
   an actionable warning otherwise (Windows without developer mode) — see
   `_make_relative_symlink`. Symlinks make a single source of truth for
   cross-tool agent assets.

This script is deliberately stdlib-only and side-effect-light: it does
nothing destructive, prints a short summary, and exits 0 on success.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

CWD = Path.cwd()


def _read_answer(key: str, default: str) -> str:
    """Read a single string value from .copier-answers.yml.

    Uses PyYAML (already a Copier dependency, so always available when this
    script is invoked by the Copier engine) so quoted strings, inline
    comments, and block scalars all parse correctly. Returns ``default``
    if the file is missing, malformed, or the key resolves to anything
    other than a string. We deliberately reject bool/int/float here
    because YAML's implicit typing happily turns ``yes``/``no``/``on``/
    ``off`` into booleans — and the only keys this helper is called on
    (``task_runner``, ``verify_command``) are always strings, so any
    other type indicates malformed answers and printing ``True`` as an
    invocation would mislead. Each newline character (including those
    produced by YAML block scalars) is replaced with a space so the
    result fits on one line when printed inside backticks; other
    internal whitespace (multiple spaces, tabs) is preserved because
    it can be intentional inside a quoted argument. Note that adjacent
    newlines therefore produce adjacent spaces — the result may contain
    runs of spaces, but it will always be a single line.
    """
    answers = CWD / ".copier-answers.yml"
    if not answers.exists():
        return default
    try:
        import yaml
    except ImportError:
        return default
    try:
        raw = answers.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except (OSError, UnicodeError, yaml.YAMLError):
        return default
    if not isinstance(data, dict):
        return default
    value = data.get(key)
    if not isinstance(value, str):
        return default
    # Normalize newlines (block-scalar YAML values can contain them) to
    # a single space so the result fits inside backticks in stdout.
    # Preserve other whitespace — internal multiple spaces or tabs may
    # be intentional inside a quoted verify_command argument.
    text = value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").strip()
    return text or default


GITIGNORE_BEGIN = "# >>> ai-agent-harness (managed by copier) >>>"
GITIGNORE_END = "# <<< ai-agent-harness (managed by copier) <<<"

GITIGNORE_BLOCK = [
    "# Personal overrides — never commit",
    "AGENTS.local.md",
    "CLAUDE.local.md",
    ".claude/settings.local.json",
    ".claude/.last_*",
    ".claude/checkpoints/",
    ".claude/shell-snapshots/",
    ".opencode/local/",
    ".codex/auth.json",
    ".cursor/settings.local.json",
    "",
    "# Agent scratch space (team decision; comment out to commit)",
    "development/work/*/scratch.md",
    ".agents/.cache/",
]


def merge_gitignore(path: Path) -> str:
    """
    Return a message describing what we did to .gitignore.

    - If the file is missing, we do nothing (the template renderer will have
      written one in greenfield mode; in brownfield mode the user likely
      doesn't have one and we don't want to surprise them).
    - If the file is present and already contains our fenced block, we leave
      it alone.
    - Otherwise, append a fresh fenced block at the end of the file.
    """
    if not path.exists():
        return "skip: .gitignore not present"

    content = path.read_text(encoding="utf-8")
    if GITIGNORE_BEGIN in content:
        return "skip: .gitignore already has managed block"

    suffix = "" if content.endswith("\n") else "\n"
    block = "\n".join([GITIGNORE_BEGIN, *GITIGNORE_BLOCK, GITIGNORE_END]) + "\n"
    path.write_text(content + suffix + "\n" + block, encoding="utf-8")
    return "appended managed block to .gitignore"


def _make_relative_symlink(link: Path, target_relative: str) -> str:
    """Create `link` -> `target_relative` if the target exists and the link is missing.

    On failure (typically Windows without Developer Mode or admin rights),
    emit an actionable warning rather than falling back to a directory copy:
    a copy would diverge silently the moment a user edits the canonical
    .agents/ source, and slash commands / skills / subagents not visible
    in the tool directory is a far less confusing failure than two
    different versions of the same file.
    """
    if link.exists() or link.is_symlink():
        return f"skip: {link} already exists"
    target_abs = (link.parent / target_relative).resolve()
    if not target_abs.exists():
        return f"skip: target {target_abs} missing"
    try:
        os.symlink(target_relative, link, target_is_directory=True)
    except OSError as e:
        return (
            f"warn: could not symlink {link} -> {target_relative}: {e}. "
            f"On Windows, enable Developer Mode (Settings > For developers) "
            f"or run as admin and re-run `copier update`. Otherwise, "
            f"recreate manually: `ln -s {target_relative} {link}` (from a "
            f"shell that supports symlinks). The canonical files live at "
            f"`{target_relative}` (relative to `{link.parent}`)."
        )
    return f"linked: {link} -> {target_relative}"


def link_agent_assets() -> Iterable[str]:
    """
    Symlink shared agent assets into tool-specific folders.

    Layout (after this runs):
        .agents/skills/       <- source of truth
        .agents/subagents/    <- source of truth
        .agents/commands/     <- source of truth
        .claude/skills        -> ../.agents/skills
        .claude/agents        -> ../.agents/subagents
        .claude/commands      -> ../.agents/commands
        .opencode/skills      -> ../.agents/skills
        .opencode/agents      -> ../.agents/subagents
        .opencode/commands    -> ../.agents/commands
    """
    pairs = [
        (Path(".claude/skills"), "../.agents/skills"),
        (Path(".claude/agents"), "../.agents/subagents"),
        (Path(".claude/commands"), "../.agents/commands"),
        (Path(".opencode/skills"), "../.agents/skills"),
        (Path(".opencode/agents"), "../.agents/subagents"),
        (Path(".opencode/commands"), "../.agents/commands"),
    ]
    for link, rel in pairs:
        link.parent.mkdir(parents=True, exist_ok=True)
        yield _make_relative_symlink(link, rel)


def main() -> int:
    messages = []
    messages.append(merge_gitignore(CWD / ".gitignore"))
    messages.extend(link_agent_assets())

    print()
    print("AI agent harness — post-generation summary")
    print("-" * 44)
    for m in messages:
        print(f"  - {m}")
    print()
    # Print the user-facing invocation, not just the raw verify_command,
    # so the suggestion also exercises the generated Makefile/justfile
    # wiring (and only falls back to verify_command for task_runner=none).
    # Default matches copier.yml's default for the same answer.
    task_runner = _read_answer("task_runner", "make")
    if task_runner in ("make", "just"):
        verify_invocation = f"{task_runner} verify"
    elif task_runner == "none":
        verify_invocation = _read_answer("verify_command", "./scripts/verify.sh")
    else:
        # Unknown task_runner value (e.g. manual edit with wrong casing): fall
        # back to the template default rather than printing verify_command raw.
        verify_invocation = "make verify"
    print("Next steps:")
    print("  1. Open AGENTS.md and tighten it for your project (target ≤200 lines).")
    print(f"  2. Run `{verify_invocation}` to confirm the toolchain wiring.")
    print("  3. Commit and push; subsequent runs use `copier update`.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
