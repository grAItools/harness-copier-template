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


def _read_untranslated(path: Path) -> str:
    """Read text with newline translation off, so CRLF survives a round trip.

    `Path.read_text` opens in universal-newlines mode, which turns every
    CRLF into a bare LF before we ever see the content; writing it back
    then rewrites the whole file on a CRLF checkout. `newline=""` hands us
    the bytes as they are.
    """
    with path.open("r", encoding="utf-8", newline="") as fh:
        return fh.read()


def _write_untranslated(path: Path, text: str) -> None:
    """Write text verbatim — no LF -> os.linesep translation on the way out."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def _newline_of(line: str, default: str = "\n") -> str:
    """The terminator of one line, or `default` if it has none."""
    for ending in ("\r\n", "\r", "\n"):
        if line.endswith(ending):
            return ending
    return default


def _prevailing_newline(lines: list[str]) -> str:
    """The terminator of the last terminated line — what inserts should match."""
    for line in reversed(lines):
        ending = _newline_of(line, "")
        if ending:
            return ending
    return "\n"


def _block_bounds(lines: list[str]) -> "tuple[int, int | None] | None":
    """Locate the fenced block.

    Returns None when there is no begin marker, `(begin, end)` for a
    well-formed fence, and `(begin, None)` when a begin marker has no
    matching end. The caller must keep those last two apart: treating a
    half-open fence as "absent" would append a second block, leaving the
    file with two begin markers and every line between them newly inside
    the managed fence.
    """
    begin = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if begin is None and stripped == GITIGNORE_BEGIN:
            begin = i
        elif begin is not None and stripped == GITIGNORE_END:
            return begin, i
    return None if begin is None else (begin, None)


def merge_gitignore(path: Path) -> str:
    """
    Return a message describing what we did to .gitignore.

    - If the file is missing, we do nothing (the template renderer will have
      written one in greenfield mode; in brownfield mode the user likely
      doesn't have one and we don't want to surprise them).
    - If the fenced block is absent, append a fresh one at the end.
    - If the fence is half-open (a begin marker with no end), we warn and
      write nothing. Only a hand-edit produces that state, and either
      repair — appending an end marker, or appending a whole second block —
      would guess at which of the following lines the user meant to manage.
    - If the fenced block is present, append only the entries it is missing,
      just above the closing marker. This is what makes a `copier update`
      that adds a new harness entry reach repos generated by an older
      template version; skipping the whole block on sight would strand them.

    An entry the user has commented out inside the block counts as present:
    the scratch-space line ships documented as opt-out ("comment out to
    commit"), and re-adding it on every update would silently undo that
    choice.

    Lines outside the fence are never touched, byte for byte: we read and
    write with newline translation off and keep each line's own terminator,
    so a CRLF `.gitignore` stays CRLF and `copier update` produces a diff
    of only the lines we actually inserted. Inserted lines take the
    terminator the file already uses.
    """
    if not path.exists():
        return "skip: .gitignore not present"

    content = _read_untranslated(path)
    lines = content.splitlines(keepends=True)
    bounds = _block_bounds(lines)

    if bounds is not None and bounds[1] is None:
        return (
            f"warn: .gitignore has `{GITIGNORE_BEGIN}` with no matching "
            f"`{GITIGNORE_END}` — left untouched. Restore the end marker (or "
            f"delete the stray begin marker) and re-run `copier update`; "
            f"harness entries are not managed until the fence is closed."
        )

    if bounds is None:
        nl = _prevailing_newline(lines)
        terminated = not content or content.endswith(("\n", "\r"))
        block = nl.join([GITIGNORE_BEGIN, *GITIGNORE_BLOCK, GITIGNORE_END]) + nl
        _write_untranslated(path, content + ("" if terminated else nl) + nl + block)
        return "appended managed block to .gitignore"

    begin, end = bounds
    present = set()
    for line in lines[begin + 1 : end]:
        stripped = line.strip()
        if not stripped:
            continue
        present.add(stripped)
        if stripped.startswith("#"):
            present.add(stripped.lstrip("#").strip())

    missing = [
        entry
        for entry in GITIGNORE_BLOCK
        if entry.strip() and not entry.startswith("#") and entry not in present
    ]
    if not missing:
        return "skip: .gitignore managed block already complete"

    nl = _newline_of(lines[end], _prevailing_newline(lines))
    lines[end:end] = [entry + nl for entry in missing]
    _write_untranslated(path, "".join(lines))
    return "added to .gitignore managed block: " + ", ".join(missing)


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
