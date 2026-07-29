# 18. Update propagation: docs split by ownership, legacy answers, reconciled gitignore block

## Status

Accepted (2026-07-30). Amends ADR 0010 (the generated `development/` tree:
two of its documents change ownership) and ADR 0012 (the simplification
wave: two of its removed questions get a legacy-consumption path); prompted
by issues #42 and #47.

## Context

A downstream repo running a routine `copier update` silently got a worse
result than a fresh render, three ways:

1. **`_skip_if_exists` froze the two harness-reference docs.** All seven
   `development/` documents were on the list. That is right for project
   content — nobody wants a regenerated `architecture.md` — but
   `harness-usage.md` and `tool-bootstrap.md` describe how the *harness
   itself* behaves: which hooks run, what each exit code means, how the
   deny-list matches. Once generated, copier skipped them forever, with no
   conflict and no notice; verified on a real v0.7.0 → main update where
   both files had upstream fixes and neither changed downstream. These are
   the files an agent reads to learn what the hooks will do to it — a repo
   generated at v0.5.0 still told its agents the old Stop-hook posture.
2. **Dropped questions regressed recorded policies.** The v0.7.0 wave
   (ADR 0012) removed `license` and `pr_merge_strategy`. A repo that had
   recorded `license: BSD-3-Clause` woke up with a `_Fill in:_` marker; a
   recorded squash-merge policy dissolved into "check the repo's GitHub
   merge settings", while the repo's own workflows kept enforcing
   squash-style titles.
3. **The managed `.gitignore` block only accreted.** The post-generation
   hook appended missing entries but never removed ones the template
   stopped managing, so the stale `specs/*/scratch.md` line outlived the
   layout change that obsoleted it. (Cosmetically, the hook's summary also
   printed three times per update — once per replay render copier performs.)

Empirical findings the decision rests on (copier 9.17):

- A file removed from `_skip_if_exists` is patched on update via copier's
  three-way merge: template changes arrive, local edits survive or surface
  as `<<<<<<< before updating` conflict markers. Nothing is silent.
- An answers-file entry that matches **no** question is passed into the
  render context, but is dropped from the regenerated answers file — so a
  template that merely consumes it regresses one update *later*, silently.
- Declaring the removed question `when: false` is worse: a skipped
  question ignores the recorded answer entirely and substitutes its
  default on the very first update.
- Update tasks run three times (old replay, real destination, new replay),
  all reporting `_copier_operation == "update"`; the replays are
  distinguishable only by not yet being git work trees when tasks run.

## Decision

1. **Split `development/` by ownership, not directory.** `harness-usage.md`
   and `tool-bootstrap.md` leave `_skip_if_exists` and become
   template-owned: every `copier update` refreshes them, and each carries a
   blockquote saying so. A new project-owned `development/harness-notes.md`
   (on `_skip_if_exists`, linked from both) is where free-form local notes
   go, so the template-owned files can stay pristine downstream and merge
   cleanly forever. The files keep their names and paths — a rename would
   orphan the downstream copy and turn the migration into a second trap;
   with the in-place split, the first update after upgrading merges the
   accumulated template changes into the existing file, loudly where local
   edits overlap.
2. **Consume legacy answers instead of re-asking or freezing them.**
   Templates render `license` and `pr_merge_strategy` behind
   `is defined`-guards, and the answers-file template re-records both keys
   whenever they are present, closing the drop-on-next-update hole. The
   questions are *not* re-added, not even `when: false` (which would
   substitute defaults over recorded answers); fresh renders get the
   neutral scaffold, and `--data` can opt in explicitly. The third
   regression the issue reported — the softened dependency-ADR rule — is
   backed by no answer, so it gets an upgrade-notes entry instead of a
   mechanism.
3. **Reconcile the managed gitignore block.** Inside its `>>> <<<` markers
   the hook now rewrites the block to the current template's entry set:
   missing entries are added, no-longer-managed entries dropped,
   commented-out entries preserved verbatim (the documented opt-out), and
   the summary reports what changed. Outside the markers the hook remains
   non-destructive, byte for byte.
4. **One summary per update.** The task line passes `_copier_operation`
   (with a `default('copy')` guard for older copier) and the hook stays
   silent when the operation is `update` and the working directory is not
   inside a git work tree — exactly the replay renders, which copier
   git-initializes only after tasks run, while an update's real destination
   is git-tracked by definition. The replays still do the work (parity
   keeps the update diff clean); they just don't report. Updates *from*
   pre-split versions still print one extra banner from the old replay's
   old hook; that run is beyond this template's reach.

## Consequences

- Fixes to the two harness-reference docs now reach every repo on its next
  update. Downstream repos that hand-edited them see one-time conflict
  markers on the first update after upgrading; the upgrade notes tell them
  to move local notes to `harness-notes.md` and take the template side.
- A recorded `license` / `pr_merge_strategy` renders tailored prose again
  and survives arbitrarily many updates. The cost is a small permanent
  ledger: `copier.yml` documents the legacy keys, and the answers-file
  template carries one guarded line per key. New legacy keys must be added
  there if a future wave removes more consumed questions.
- The managed gitignore block is now exactly what the current template
  says, plus the user's commented-out opt-outs. A user line *inside* the
  fence is dropped on the next run (reported in the summary); the fence has
  always said "managed by copier", and the README now states the contract
  explicitly.
- `copier update` prints one summary (two when coming from a pre-split
  version), and its "Next steps" onboarding block is reserved for copies.
- `development/` gains one file. The ownership boundary is now legible in
  the tree itself: template-owned docs say so in a blockquote, and the
  project-owned notes file exists precisely so the distinction costs
  downstream nothing.

## Alternatives considered

- **Extracting the hook/exit-code reference into a new always-regenerated
  file and leaving `harness-usage.md` project-owned** (the issue's first
  sketch). Rejected: nearly all of `harness-usage.md` is template prose —
  downstream carried exactly two local notes — so the split would move the
  whole document to a new name, orphan the old file in every downstream
  repo, and still leave a project-owned shell that rots. Keeping the name
  and flipping ownership preserves history and makes the migration a
  merge, not a rename.
- **Documenting the freeze in the upgrade notes only** (the issue's
  fallback). Rejected as primary: it converts a silent failure into a
  documented manual chore, but the chore recurs every release and each
  release it is skipped re-opens the gap.
- **Re-adding the removed questions with `when: false`.** Rejected on
  measurement: copier substitutes the default for skipped questions,
  overriding the recorded answer — the exact regression being fixed.
- **Keeping append-only gitignore merging and deleting stale entries via a
  one-off migration.** Rejected: the next removed entry recreates the
  problem; reconciliation is the steady-state rule the markers already
  imply.
