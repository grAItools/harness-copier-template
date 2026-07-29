#!/usr/bin/env python3
"""
Post-generation copier task.

Runs in the *destination* directory after all template files are rendered.

Responsibilities
----------------
1. Reconcile the fenced agent-harness block of the destination .gitignore
   against GITIGNORE_BLOCK: append the block when absent, otherwise rewrite
   the fence's contents to the current entry set — adding what's missing,
   dropping entries the template no longer manages, and preserving entries
   the user commented out. Nothing outside the fence is ever touched.
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
    - If the fenced block is present, reconcile its contents against
      GITIGNORE_BLOCK: entries the current template manages are (re)written
      in canonical order, entries it no longer manages are dropped. Merely
      appending what's missing let the block accrete forever — a repo
      generated when the scratch space lived at `specs/*/scratch.md` kept
      that stale line through every update. The markers say "managed by
      copier", so inside them the template's set is authoritative; anything
      a user wants ignored on top belongs outside the fence.

    An entry the user has commented out inside the block stays commented
    out, byte for byte: the scratch-space line ships documented as opt-out
    ("comment out to commit"), and rewriting it active on every update would
    silently undo that choice.

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
        prefix = content + ("" if terminated else nl)
        if content.strip():
            # Blank line separating the user's own entries from ours. Skipped
            # when there are none to separate from, so an empty .gitignore
            # starts at the begin marker rather than a stray blank line.
            # Whitespace-only content is still kept verbatim, never trimmed.
            prefix += nl
        block = nl.join([GITIGNORE_BEGIN, *GITIGNORE_BLOCK, GITIGNORE_END]) + nl
        _write_untranslated(path, prefix + block)
        return "appended managed block to .gitignore"

    begin, end = bounds
    active = set()
    commented = {}
    for line in lines[begin + 1 : end]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            entry = stripped.lstrip("#").strip()
            if entry in GITIGNORE_BLOCK:
                commented.setdefault(entry, line)
        else:
            active.add(stripped)

    nl = _newline_of(lines[end], _prevailing_newline(lines))
    new_block = []
    for entry in GITIGNORE_BLOCK:
        opted_out = entry in commented and entry not in active
        if entry.strip() and not entry.startswith("#") and opted_out:
            kept = commented[entry]
            new_block.append(kept if _newline_of(kept, "") else kept + nl)
        else:
            new_block.append(entry + nl)

    if new_block == lines[begin + 1 : end]:
        return "skip: .gitignore managed block already in sync"

    managed = {e for e in GITIGNORE_BLOCK if e.strip() and not e.startswith("#")}
    added = [
        e for e in GITIGNORE_BLOCK
        if e in managed and e not in active and e not in commented
    ]
    removed = sorted(active - managed)
    lines[begin + 1 : end] = new_block
    _write_untranslated(path, "".join(lines))
    details = "; ".join(
        f"{verb}: {', '.join(entries)}"
        for verb, entries in (("added", added), ("removed", removed))
        if entries
    )
    return "reconciled .gitignore managed block" + (
        f" ({details})" if details else " (formatting only)"
    )


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


def _is_update_replay(operation: str) -> bool:
    """True when this run is one of `copier update`'s temporary replays.

    An update renders the old and new template versions into throwaway
    directories to compute the diff it applies, and tasks run in each — three
    runs, three summaries, for one update. The replays are distinguishable
    because copier git-initializes them only *after* tasks have run, while the
    real destination of an update is required to be git-tracked already. Plain
    `copier copy` never reports the "update" operation, so a greenfield render
    into a not-yet-git directory stays verbose.
    """
    if operation != "update":
        return False
    path = CWD.resolve()
    return not any((p / ".git").exists() for p in (path, *path.parents))


def main() -> int:
    # argv[1] is `{{ _copier_operation }}` ("copy" / "recopy" / "update"),
    # empty or absent under copier versions that predate the variable — then
    # we assume "copy" and stay verbose.
    operation = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else "copy"

    messages = []
    messages.append(merge_gitignore(CWD / ".gitignore"))
    messages.extend(link_agent_assets())

    if _is_update_replay(operation):
        # Still do the work above — replay parity keeps the update diff
        # clean — but say nothing: the run in the real destination reports.
        return 0

    print()
    print("AI agent harness — post-generation summary")
    print("-" * 44)
    for m in messages:
        print(f"  - {m}")
    print()
    if operation != "update":
        print("Next steps:")
        print(
            "  1. Open AGENTS.md and tighten it for your project (target ≤200 lines)."
        )
        print(
            "  2. Run your verify target — `make verify` / `just verify` / your "
            "configured verify command — to confirm the toolchain wiring."
        )
        print("  3. Commit and push; subsequent runs use `copier update`.")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
