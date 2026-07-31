#!/usr/bin/env sh
# block-destructive.sh — canonical destructive-command matcher.
#
# Reads candidate command text on stdin; exits 2 (with a message naming what
# matched, so a deny is distinguishable from an infrastructure failure) if the
# command *runs* a forbidden operation, 0 otherwise. This is the single source
# of truth for the deny-list.
#
# It matches text, not intent — but it does separate a pattern that is run from
# one merely mentioned inside quotes, so read-only commands that quote a
# deny-listed string (a grep pattern, `git log --grep=…`, a printf'd fixture, a
# commit message) are allowed. Three rules:
#
#   1. an operation reachable without crossing a quote — after
#      resolving escapes and $'…' strings, with quote state carried
#      across lines — is run, not mentioned                    -> deny
#      (`push --force` followed by `-` is a longer, lease-checked
#      flag — --force-with-lease, --force-if-includes — not the
#      operation)
#   2. the string another shell will run is held to the same rules,
#      recursively: a runner's argument (`sh … -c` wherever the -c
#      sits, ssh / eval / su, including inside `…`); anything
#      produced ahead of a pipe into a shell, whatever the producer
#      (compound command, earlier statement) and whatever prefixes
#      the shell (sudo, env, timeout 5, LC_ALL=C, …); and a command
#      that both mentions an operation and runs a shell on a file
#      (`… > s.sh; sh s.sh`, `sh < s.sh`), where being quoted does
#      not make it a mention                                    -> deny
#      Both rules run twice: once over the whole text, once per
#      line, so an unpaired quote cannot hide a later line from
#      either. Recursion is bounded by depth and by a work budget;
#      past it the remaining text gets a flat, conservative check.
#   3. a text pattern anywhere, quoted or not — SQL only ever
#      appears as a quoted argument, so its mention and its use
#      are indistinguishable                                    -> deny
#
# Surviving false positives, each explained by the deny message it triggers: a
# quoted mention of a rule-3 pattern; a heredoc body whose lines read as
# commands; a multi-line quoted string whose lines read as commands (the
# per-line pass parses each line alone, exactly so a quote left open on one
# line cannot hide a bare operation on the next); and a quoted mention in a
# command that also runs a shell on a file. Recovery is a rephrase — usually
# splitting into two calls — not a different task.
#
# Blind spots: `eval` of a variable, "$(…)" inside a double-quoted span,
# aliases and shell functions, encoded payloads, any other language doing the
# same work (`python -c`), a wrapper taking option arguments before the shell
# (`… | sudo -u user sh`), a word spliced across a quote (`rm -r'f' x` — the
# shell joins it, this matcher does not, because joining spliced words would
# re-deny `grep -e'rm -rf' notes.txt`), and a shell run from a file written in
# an *earlier* tool call — the same-command write-then-run form is denied by
# rule 2. This is a backstop against accidents, not a sandbox.
#
# The verdict is computed by the python3 program below, not by `grep -qE` as
# before: the single-pass regex grammar did quote tracking, runner detection
# and operation matching in one line-oriented pattern, and issue #40 showed
# eight deny→allow regressions it could not close (quote spans that cross
# lines, $'…' quoting, quotes nested inside a runner string, multi-segment
# pipes) plus a locale-dependent verdict from byte-range matching. python3 is
# already the hooks' fallback JSON parser (ADR 0013) and is probed here the
# same way — by running it, since a stub can resolve and then fail. A missing
# python3 fails CLOSED with the remedy: a guard that silently stops guarding
# is worse than a loud dependency. So does an interpreter that starts and then
# cannot reach a verdict: an allow counts only as exit 0 carrying the program's
# token on stdout, and every other status denies. See ADR 0017.
#
# Consumers:
#   - Claude Code: the PreToolUse(Bash) hook in .claude/settings.json pipes the
#     tool input here. Its SessionStart self-test runs one command per rule
#     through this script and counts a deny only as exit 2 *plus* stderr
#     opening with `block-destructive: denied` — dash exits 2 for an unopenable
#     script too. That prefix is a cross-file contract (ADR 0016): reword the
#     deny message and the self-test must move with it.
#   - OpenCode: cannot call a script, so the deny globs in
#     .opencode/opencode.jsonc restate these patterns by hand — as plain
#     substrings, since a glob can express neither rule 1 nor rule 1's
#     lease-checked-flag exception, so OpenCode still denies both the quoted
#     mentions and `push --force-with-lease` that this script allows. Keep the
#     patterns in sync; the divergence is stricter by design, never looser.
#
# See .agents/README.md for the single-source-of-truth rationale.

# --- deny-list (mirror any change into .opencode/opencode.jsonc) -------------
# Patterns are literal strings separated by `|`, not regexes.
# Destructive operations: denied when run, allowed when quoted (rules 1 and 2).
operations='rm -rf|push --force|reset --hard'
# Denied anywhere in the command text, quoted or not (rule 3).
text_patterns='DROP TABLE'
# Shell names are matched as whole words (a path prefix is allowed), never as
# an `sh` suffix: `push` and `refresh` end in `sh` too, and a suffix match
# would deny `git push -c k=v` the moment the line mentioned an operation.
shells='sh|bash|dash|zsh|ksh|ash'
# -----------------------------------------------------------------------------

# Fail closed, legibly, when the matcher's interpreter is missing. Run-probed
# like hook-input.sh: stock macOS ships a /usr/bin/python3 stub that resolves
# but cannot run until the Command Line Tools are installed.
if ! python3 -c '' >/dev/null 2>&1; then
	printf '%s\n' 'block-destructive: denied - cannot check this command: python3 is missing or unable to run, and the deny-list matcher needs it. Install python3 (apt-get install python3 / xcode-select --install), from a shell outside the agent if needed.' >&2
	exit 2
fi

program=$(cat <<'PYEOF'
import os
import re
import sys


def env_list(name):
    raw = os.environ.get(name, "").strip()
    # Tolerate the pre-tokenizer spelling of `shells`, which was an ERE group:
    # a downstream repo that customised '(sh|bash|…)' and kept its own line
    # through a copier update must not end up with a list of '(sh' and 'ash)'.
    if raw.startswith("(") and raw.endswith(")"):
        raw = raw[1:-1]
    return [p.strip() for p in raw.split("|") if p.strip()]


OPERATIONS = env_list("BLOCK_OPERATIONS")
TEXT_PATTERNS = env_list("BLOCK_TEXT_PATTERNS")
SHELLS = set(env_list("BLOCK_SHELLS"))
OPS_RAW = os.environ.get("BLOCK_OPERATIONS", "")
PATS_RAW = os.environ.get("BLOCK_TEXT_PATTERNS", "")

# Commands that run a string argument rather than read one. `su` runs its -c
# argument; it is grouped here rather than with the shells because its
# operand (the user) is not a script file.
RUNNERS = ("ssh", "eval", "su")
# Prefix commands a piped-into or file-running shell may hide behind. Wrappers
# taking option *arguments* (`sudo -u user sh`) are a known blind spot.
WRAPPERS = ("sudo", "doas", "env", "nohup", "timeout", "time", "command",
            "exec", "setsid", "stdbuf", "nice", "ionice", "xargs")
C_CLUSTER = re.compile(r"-[A-Za-z0-9]*c")  # -c anywhere in a one-dash cluster
DURATION = re.compile(r"[0-9]+[smhd]?\Z")  # `timeout 5`'s operand
ASSIGN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")  # `LC_ALL=C sh` prefix
MAX_DEPTH = 6
# Recursion is bounded by work, not just depth: every runner token re-enters
# check() on the rest of its command, so a line of them costs exponentially.
# Past the budget the remaining text gets the flat, conservative check.
BUDGET = 64
_calls = [0]

RULE1_MSG = """the command runs a deny-listed destructive operation.
  Deny-list: {ops}.
  Only occurrences reachable without crossing a quote are denied, so a mention
  inside quotes (a search pattern, a fixture, a commit message) passes. This
  one was reachable, so it is blocked by design."""

RULE2_MSG = """the command passes a deny-listed destructive operation to a nested
  shell to run — as a runner's argument (sh -c / ssh / eval / su), piped in as
  a script (... | sh), or written alongside a shell invoked on a file — where
  being quoted is not a mention.
  Deny-list: {ops}. Blocked by design."""

RULE3_MSG = """the command text contains {pats}. This pattern is denied
  anywhere, quoted or not, because SQL only ever appears as a quoted argument,
  so a mention of it cannot be told apart from a use. To search for it, use a
  pattern that avoids the literal (e.g. DROP TABL[E])."""


def deny(msg):
    sys.stderr.write("block-destructive: denied - " + msg + "\n")
    sys.exit(2)


def scan(text):
    """One pass over text with the shell's quoting rules.

    Returns (view, pipelines): `view` is the text reachable without crossing
    a quote — quoted spans elided, escapes and $'…' resolved, backslash-
    newline joined, newlines preserved; `pipelines` is a list of pipelines,
    each a list of (tokens, raw_text, start, piped_in) simple commands, where
    tokens are (resolved_value, is_redirect_target) pairs and `piped_in` says
    the segment reads another command's output. An unterminated quote runs to
    the end of text: the remainder could not have executed as written.
    """
    n = len(text)
    i = 0
    view = []
    pipelines = []
    segments = []
    tokens = []
    word = []
    in_word = False
    redirect_next = False
    seg_start = 0
    seg_piped = False
    after_pipe = False

    def flush_word():
        nonlocal word, in_word, redirect_next
        if in_word:
            tokens.append(("".join(word), redirect_next))
            redirect_next = False
        word = []
        in_word = False

    def end_segment(pos, piped_next=False):
        nonlocal tokens, seg_start, seg_piped, redirect_next
        flush_word()
        redirect_next = False  # a redirect with no operand cannot leak a flag
        if tokens:
            segments.append((tokens, text[seg_start:pos], seg_start, seg_piped))
        tokens = []
        seg_start = pos + 1
        seg_piped = piped_next

    def end_statement(pos):
        nonlocal segments
        end_segment(pos)
        if segments:
            pipelines.append(segments)
        segments = []

    while i < n:
        ch = text[i]
        was_pipe = after_pipe
        after_pipe = False
        if ch == "$" and i + 1 < n and text[i + 1] == "'":
            i += 2  # bash $'…': backslash escapes anything, including \'
            in_word = True
            while i < n:
                c = text[i]
                if c == "\\" and i + 1 < n:
                    word.append(text[i + 1])
                    i += 2
                elif c == "'":
                    i += 1
                    break
                else:
                    word.append(c)
                    i += 1
        elif ch == "'":
            j = text.find("'", i + 1)
            end = n if j < 0 else j
            word.append(text[i + 1:end])
            in_word = True
            i = end + 1
        elif ch == '"' or (ch == "$" and i + 1 < n and text[i + 1] == '"'):
            i += 2 if ch == "$" else 1
            in_word = True
            while i < n:
                c = text[i]
                if c == "\\" and i + 1 < n:
                    nxt = text[i + 1]
                    if nxt == "\n":
                        i += 2  # line continuation inside "…": removed
                    elif nxt in '"\\$`':
                        word.append(nxt)
                        i += 2
                    else:
                        word.append(c)  # backslash stays literal
                        i += 1
                elif c == '"':
                    i += 1
                    break
                else:
                    word.append(c)
                    i += 1
        elif ch == "\\":
            if i + 1 < n and text[i + 1] == "\n":
                i += 2  # line continuation: removed entirely
            elif i + 1 < n:
                # An escaped character is literal but still reachable: \rm is
                # the alias-bypass form of rm, and \' outside quotes cannot
                # open a span.
                word.append(text[i + 1])
                view.append(text[i + 1])
                in_word = True
                i += 2
            else:
                i = n
        elif ch in " \t":
            after_pipe = was_pipe  # blanks do not end a pipeline continuation
            flush_word()
            view.append(ch)
            i += 1
        elif ch == "\n" and was_pipe:
            # POSIX: a newline after `|` continues the pipeline on the next
            # line, so the reading shell is still this pipeline's consumer.
            after_pipe = True
            view.append(ch)
            i += 1
        elif ch == "\n" or ch in ";()`":
            # A backtick opens or closes a command substitution: what is inside
            # is a command of its own, so `echo `sh -c '…'`` must expose `sh`.
            end_statement(i)
            view.append(ch)
            i += 1
        elif ch == "&":
            nxt = text[i + 1] if i + 1 < n else ""
            if nxt == ">":  # &> / &>> redirection
                flush_word()
                redirect_next = True
                view.append("&>")
                i += 2
                if i < n and text[i] == ">":
                    i += 1
            else:
                end_statement(i)
                view.append("&&" if nxt == "&" else "&")
                i += 2 if nxt == "&" else 1
        elif ch == "|":
            nxt = text[i + 1] if i + 1 < n else ""
            if nxt == "|":
                end_statement(i)
                view.append("||")
                i += 2
            else:  # | or |&: next segment of the same pipeline
                end_segment(i, True)
                after_pipe = True
                view.append("|")
                i += 2 if nxt == "&" else 1
        elif ch in "<>":
            if in_word and "".join(word).isdigit():
                word = []  # fd number attached to the redirect (2>&1)
                in_word = False
            else:
                flush_word()
            redirect_next = True
            view.append(ch)
            i += 1
            while i < n and text[i] in "<>&-":
                if text[i] == "-":
                    # `2>&-` closes a descriptor: it takes no operand, so the
                    # flag must not swallow the next word (typically the shell).
                    redirect_next = False
                i += 1
        else:
            word.append(ch)
            view.append(ch)
            in_word = True
            i += 1

    end_statement(n)
    return "".join(view), pipelines


def normalize(s):
    return re.sub(r"[ \t]+", " ", s)


def op_reachable(s):
    """True when a deny-listed operation occurs in s (whitespace-collapsed).

    A match immediately followed by `-` is a longer flag — push --force-with-
    lease, push --force-if-includes — and is not the operation.
    """
    s = normalize(s)
    for op in OPERATIONS:
        start = 0
        while True:
            k = s.find(op, start)
            if k < 0:
                break
            end = k + len(op)
            if end < len(s) and s[end] == "-":
                start = k + 1
                continue
            return True
    return False


def basename(tok):
    return tok.rsplit("/", 1)[-1]


def strip_wrappers(args):
    k = 0
    while k < len(args) and (
        basename(args[k]) in WRAPPERS or ASSIGN.match(args[k])
    ):
        if ASSIGN.match(args[k]):
            k += 1  # `LC_ALL=C sh` — an assignment prefix, not the command
            continue
        k += 1
        while k < len(args) and (
            args[k].startswith("-") or "=" in args[k] or DURATION.match(args[k])
        ):
            k += 1
    return args[k:]


def runs_file(args, has_redirect_operand=False):
    """True for a shell invoked on a script file, not on -c.

    `sh s.sh` and `sh < s.sh` both run the file; the second reaches the shell
    as a redirect operand, which is not part of args.
    """
    stripped = strip_wrappers(args)
    if not stripped or basename(stripped[0]) not in SHELLS:
        return False
    for t in stripped[1:]:
        if C_CLUSTER.match(t):
            return False  # a -c runner: rule 2a's territory
        if not t.startswith("-"):
            return True
    return has_redirect_operand


def rule2(pipelines, text, depth):
    """Nested shells: a runner's argument, a pipe into a shell, a shell on a
    file. Being inside quotes is not a mention where a shell will run it."""
    for segments in pipelines:
        for tokens, _raw, start, piped_in in segments:
            args = [t for (t, is_redir) in tokens if not is_redir]
            redirected = any(is_redir for (_t, is_redir) in tokens)
            for ti, tok in enumerate(args):
                base = basename(tok)
                tail = args[ti + 1:]
                if not tail:
                    continue
                # The string a runner is handed is re-checked by these same
                # rules: an operation reachable there runs; a mention nested
                # inside further quotes is still a mention.
                if base in RUNNERS or (
                    base in SHELLS and any(C_CLUSTER.match(t) for t in tail)
                ):
                    check(" ".join(tail), depth + 1)
            if piped_in:
                stripped = strip_wrappers(args)
                if stripped and basename(stripped[0]) in SHELLS:
                    # Everything ahead of this shell in the command produced
                    # what it will run — including across `;`, `&&` and a
                    # compound producer, which is where the text was written.
                    if op_reachable(text[:start]):
                        deny(RULE2_MSG.format(ops=OPS_RAW))
            if runs_file(args, redirected) and op_reachable(text):
                deny(RULE2_MSG.format(ops=OPS_RAW))


def check(text, depth):
    """Apply rules 1 and 2 to text, recursing into nested-shell strings."""
    msg1 = RULE1_MSG if depth == 0 else RULE2_MSG
    _calls[0] += 1
    if depth > MAX_DEPTH or _calls[0] > BUDGET:
        if op_reachable(text):
            deny(RULE2_MSG.format(ops=OPS_RAW))
        return
    view, pipelines = scan(text)
    if op_reachable(view):
        deny(msg1.format(ops=OPS_RAW))
    rule2(pipelines, text, depth)
    # Per-line pass, quote state restarting on each line: an unpaired quote in
    # an earlier line (a comment's apostrophe, a heredoc body) must not hide a
    # later line — from either rule, since an open quote swallows the rest of
    # the text for the pipeline structure too. The cost is the multi-line-
    # string false positive documented in the header.
    if "\n" in text:
        for line in text.split("\n"):
            line_view, line_pipelines = scan(line)
            if op_reachable(line_view):
                deny(msg1.format(ops=OPS_RAW))
            rule2(line_pipelines, line, depth)


def main():
    # surrogateescape keeps the verdict byte-deterministic: unlike the previous
    # grep bracket-expressions, a high byte cannot flip deny/allow with locale.
    data = sys.stdin.buffer.read().decode("utf-8", "surrogateescape")

    if not OPERATIONS or not SHELLS or not TEXT_PATTERNS:
        deny("cannot check this command: a deny-list did not reach the "
             "matcher, so the variables at the top of block-destructive.sh "
             "were changed or damaged. Restore the operations/text_patterns/"
             "shells deny-list variables.")

    check(data, 0)

    for pat in TEXT_PATTERNS:
        if pat in data:
            deny(RULE3_MSG.format(pats=PATS_RAW))

    # The wrapper accepts an allow only with this token on stdout, so an
    # interpreter that starts and then fails to reach a verdict cannot read
    # as one.
    sys.stdout.write("block-destructive: allow\n")


try:
    main()
except SystemExit:
    raise  # a rule's verdict
except BaseException as exc:  # a failed check is a deny, never a pass
    deny("cannot check this command: the matcher itself failed (%s: %s). "
         "This is a bug in block-destructive.sh or an unreadable payload, "
         "not a verdict on the command." % (type(exc).__name__, exc))

sys.exit(0)
PYEOF
)

# Anything but a token-backed allow or a rule's deny is a failed check, and a
# failed check denies: `python3 -c ''` above proves an interpreter starts, not
# that it can run *this* program (a python2 shim, a stripped standard library),
# and a crash exits 1 - which PreToolUse treats as a non-blocking error, i.e.
# allows the command.
verdict=$(BLOCK_OPERATIONS="$operations" BLOCK_TEXT_PATTERNS="$text_patterns" \
	BLOCK_SHELLS="$shells" python3 -c "$program")
rc=$?

[ "$rc" -eq 0 ] && [ "$verdict" = 'block-destructive: allow' ] && exit 0
[ "$rc" -eq 2 ] && exit 2

printf '%s\n' "block-destructive: denied - cannot check this command: the deny-list matcher did not reach a verdict (python3 exited $rc). python3 runs but cannot run the matcher; any message above is its own. Repair or replace python3, from a shell outside the agent if needed." >&2
exit 2
