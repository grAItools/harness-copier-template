# 19. A negative control in the guard self-test

## Status

Accepted (2026-07-31). Amends [ADR 0016](0016-filter-shape-probe-guard-selftest-anchored-gate.md)
Decision 3; prompted by issue #52. Numbered 0019 because the currently-open
update-propagation PR already claims 0018.

## Context

ADR 0016 Decision 3 gave SessionStart a guard self-test: one command per
deny-list rule piped through `block-destructive.sh`, each required to come back
denied — exit 2 plus the guard's own `block-destructive: denied` stderr prefix.
That closed the *denies-nothing* direction (a truncated guard that runs and
exits 0) and the *denies-everything-without-its-message* direction (dash
failing to parse the script).

Every probe expects a denial, though, so the self-test cannot distinguish
**"guard working"** from **"guard denying everything with its genuine
message"**. Two reachable states produce exactly that, and both were
reproduced against a render of merged `main` (`cd408a9`):

- **Deny-list value lost** — the damage a partial write leaves. The tokenizer
  refuses to run with an empty operations list and denies every command,
  carrying the real prefix. All three probes pass; the self-test is rc 0 and
  silent; a benign `git status` is denied rc 2.
- **`python3` missing or unable to run** — routine since
  [ADR 0017](0017-deny-list-tokenizer-in-python3.md) made the matcher require
  it. The fail-closed path denies everything with the real prefix and the
  install remedy on stderr — but nothing runs that path at session start, so
  the session opens silent and wedged on any `python3`-less host.

A third state is invisible to deny-expected probes for the same reason: an
**over-broad deny-list customisation** (a pattern that matches benign
commands) passes every probe while denying commands it must not.

This is a warning-coverage gap, not a safety regression — nothing previously
denied became allowed. The failure mode is a wedged session that starts
without telling the user why, while the self-test reports health.

## Decision

**The self-test ends with a negative control.** After the three deny-expected
probes, one benign read-only command — `git status` — is piped through the
guard and must come back **exit 0**. Anything else warns with the same
non-blocking exit 1 posture as the rest of the self-test, quoting the guard's
own stderr, which names the cause (the lost deny-list, the missing
interpreter, or the pattern that matched). The remedy line defers to the
guard's message when it names one, and falls back to restoring
`block-destructive.sh` otherwise.

The control was verified to discriminate across all four relevant states:

| State | Benign control | Self-test outcome |
|---|---|---|
| Healthy (tokenizer, `python3` present) | allowed, rc 0 | silent, rc 0 |
| Deny-list value lost | denied, rc 2 | warns, rc 1 |
| `python3` missing/unable to run | denied, rc 2 | warns, rc 1 |
| Over-broad deny-list customisation | denied, rc 2 | warns, rc 1 |

`git status` is the control because it is read-only, sits in
`permissions.allow`, and shares no substring with the shipped deny-list or
text patterns.

## Consequences

- A deny-everything guard now warns at session start instead of wedging the
  session silently; the warning carries the guard's own diagnosis, so the
  `python3` case surfaces its install remedy at the session's first moment
  rather than at the first denied Bash call.
- One additional guard invocation per session start.
- `git status` staying allowed by the guard becomes part of the self-test's
  contract, alongside the `block-destructive: denied` prefix ADR 0016 already
  pinned. A downstream repo that customises the deny-list to match `git
  status` will start every session with this warning — which is the control
  doing its job, and the warning quotes the pattern that matched.
