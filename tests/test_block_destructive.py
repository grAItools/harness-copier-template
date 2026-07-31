"""Behaviour lock for template/.agents/hooks/block-destructive.sh.

The guard is the harness's only Bash backstop and ships verbatim (no Jinja),
so the template source tested here is byte-identical to what downstream repos
receive. Every case is a string fed to the matcher on stdin — nothing in this
file executes a destructive command.

Run with either of:

    python3 -m unittest discover tests
    python3 tests/test_block_destructive.py

The tables pin three kinds of verdict:
  - true positives that every version of the guard must deny;
  - the fail-open regressions of issue #40, denied again since ADR 0017;
  - the false positives issue #36 / ADR 0015 fixed, which must stay allowed.
Documented *surviving* false positives are pinned as denials on purpose: a
change that silently flips them is a behaviour change to re-document, not an
accidental improvement.
"""

import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GUARD = PROJECT_ROOT / "template" / ".agents" / "hooks" / "block-destructive.sh"
SH = shutil.which("sh") or "sh"

ALLOW = 0
DENY = 2


def verdict(command, env=None):
    """Exit code of the guard for command text (str or bytes) on stdin."""
    data = command.encode() if isinstance(command, str) else command
    result = subprocess.run(
        [SH, str(GUARD)], input=data, capture_output=True, env=env
    )
    return result


TRUE_POSITIVES = [
    # Plain, chained, and wrapped forms.
    "rm -rf /tmp/x",
    "cd x && rm -rf y",
    "git push --force origin main",
    "git push --force",
    "git reset --hard origin/main",
    "git -C /repo push --force",
    "\\rm -rf /tmp/x",  # alias-bypass backslash is still the operation
    "sudo rm -rf /var/cache",
    "find . -name x -exec rm -rf {} +",
    "ls | xargs rm -rf",
    "$(rm -rf /tmp/x)",
    "`rm -rf /tmp/x`",
    "git commit -m 'msg' && git push --force",
    # An escaped quote inside a quoted argument must not flip quote parity.
    'git commit -m "see \\"docs\\"" && git push --force',
    # Nested shells: quoting is not a mention in the string a runner runs.
    "sh -c 'rm -rf /tmp/x'",
    "sh -c 'cd x && rm -rf y'",
    'bash -c "sh -c \'rm -rf /tmp/x\'"',  # two levels down
    'xargs -I{} sh -c "rm -rf {}"',
    'sudo -u x sh -c "rm -rf /tmp/y"',
    "ssh host 'rm -rf /srv/data'",
    "ssh host rm -rf /srv/data",
    'ssh host "cd /srv && rm -rf data"',
    'eval "rm -rf $dir"',
    "su -c 'rm -rf /srv/data' deploy",
    "echo 'rm -rf /data' | sh",
    "echo 'rm -rf /data' | sudo sh",
    # Multi-line command: the second line runs bare.
    "git fetch\nrm -rf build",
    # An empty quoted span inside a word does not break the operation up.
    # (A *non-empty* span does, and is not caught — see DOCUMENTED_BLIND_SPOTS.)
    "r''m -rf /tmp/x",
    # Whitespace variants the shell reads as the same command.
    "rm  -rf /tmp/x",
    "rm\t-rf /tmp/x",
    # Rule 3: SQL is denied quoted or not.
    "psql -c 'DROP TABLE users'",
    "grep -rn 'DROP TABLE' .",
]

ISSUE_40_REGRESSIONS = [
    # A quoted word inside the runner's script must not hide the operation.
    "bash -c 'git fetch && echo \"resetting\" && git reset --hard origin/main'",
    # -c parses wherever it sits, not only adjacent to the shell name.
    "bash -euo pipefail -c 'rm -rf /tmp/x'",
    "bash --norc -c 'rm -rf /tmp/x'",
    'bash -euo pipefail -c "rm -rf /tmp/x"',
    # A multi-line quoted argument must not strand the trailing operation.
    'git commit -m "fix: thing\n\nLonger body." && rm -rf build',
    # $'…' permits \' inside; the parity model must not desynchronise.
    "git commit -m $'fix don\\'t break' && rm -rf build",
    # Pipes into a shell cross any number of segments and common wrappers.
    "echo 'rm -rf /data' | tee /tmp/x | sh",
    "echo 'rm -rf /data' | env sh",
    "echo 'rm -rf /data' | cat | timeout 5 sh",
    "echo 'rm -rf /data' | nohup sh",
    # Write-then-run in one command: the mention becomes a script.
    "printf 'rm -rf /tmp/x' > s.sh; sh s.sh",
]

# Fail-opens found reviewing the tokenizer itself: every one of these was
# denied by the pre-tokenizer matcher (or by v0.7.0) and must stay denied.
REVIEW_FOUND_FAIL_OPENS = [
    # The producer ahead of a pipe into a shell can be any compound command,
    # and the pipeline may continue on the next line.
    "(echo 'rm -rf /data') | sh",
    "{ echo 'rm -rf /data'; } | sh",
    "for f in a; do echo 'rm -rf /data'; done | sh",
    "if true; then echo 'rm -rf /data'; fi | sh",
    "echo 'rm -rf /data' |\n  sh",
    # A descriptor-closing redirect takes no operand: it must not swallow the
    # shell that follows it.
    "cat notes.txt 2>&- ; sh -c 'rm -rf /tmp/y'",
    "echo 'rm -rf /data' >&- | sh",
    "exec 3>&- ; ssh host 'rm -rf /srv/data'",
    # Write-then-run also spells the run as a pipe or a redirect.
    "printf 'rm -rf /tmp/x' > s.sh && cat s.sh | sh",
    "printf 'rm -rf /tmp/x' > s.sh; cat s.sh | sh",
    "printf 'rm -rf /x' > s.sh; sh < s.sh",
    # An unpaired quote on an earlier line must not disable rule 2 below it.
    'echo "unclosed\nsh -c \'rm -rf /data\'',
    'cat <<EOF\nhe said "hi\nEOF\nsh -c \'rm -rf /x\'',
    # Backtick substitution runs a command too.
    "echo `sh -c 'rm -rf /tmp/x'`",
    "x=`bash -c 'rm -rf /tmp/x'`",
    # An assignment prefix is not the command name.
    "echo 'rm -rf /data' | LC_ALL=C sh",
    "echo 'rm -rf /data' | PATH=/bin sh -s",
    # The recursion budget must bound cost without losing the verdict.
    "ssh h " * 60 + "rm -rf /tmp/x",
]

# Evasion shapes the guard does not catch, kept explicit so the suite does not
# certify coverage it lacks. The guard is a backstop against accidents, not a
# sandbox (see the script header); the pre-tokenizer matcher missed these too.
DOCUMENTED_BLIND_SPOTS = [
    # A word spliced from quoted and unquoted parts. Joining spliced words
    # into rule 1 would re-deny `grep -e'rm -rf' notes.txt`, a read-only
    # mention of exactly the class ADR 0015 exists to allow.
    "rm -r'f' /tmp/x",
    'git reset --"hard" origin/main',
    "git push --f'o'rce origin main",
    # A wrapper taking an option argument before the shell.
    "echo 'rm -rf /data' | sudo -u deploy sh",
]

DOCUMENTED_SURVIVING_FALSE_POSITIVES = [
    # A multi-line quoted string whose lines read as commands: the per-line
    # pass sees them bare. The price of not letting an unpaired quote on one
    # line hide a bare operation on the next (see the script header).
    'git commit -m "subject\n\nnever run rm -rf here"',
    # A heredoc body reads as command lines.
    "cat <<EOF\nrm -rf /tmp/x\nEOF",
    # A quoted mention alongside a shell run on a file (rule 2's file form).
    "grep 'rm -rf' notes.txt && sh build.sh",
]

FALSE_POSITIVES_FIXED_BY_ADR_0015 = [
    # Quoted mentions in read-only commands (issue #36).
    "grep -rn 'rm -rf' .",
    "rg 'reset --hard' development/",
    "git log --grep='push --force'",
    "git commit -m 'note: never run rm -rf here'",
    "printf '%s\\n' 'rm -rf /tmp/x' > fixture.txt",
    'git commit -m "8\\" display" && git status',
    "ssh host uptime && grep -rn 'rm -rf' .",
    "grep 'rm -rf' . | ssh host tee f",
    "grep -rn 'rm -rf' . | git push",  # `push` must not read as a shell
    "git push -c k=v && grep 'rm -rf' .",
    "grep -c 'rm -rf' file",  # -c on a non-shell is not a runner
    "grep -e'rm -rf' notes.txt",  # a mention spliced onto a flag is a mention
]

FALSE_POSITIVES_FIXED_BY_ADR_0017 = [
    # The lease-checked pushes are longer flags, not `push --force`.
    "git push --force-with-lease origin main",
    "git push --force-with-lease=main:abc123 origin main",
    "git push --force-if-includes --force-with-lease origin main",
    # A mention nested inside a runner's string recurses to a mention.
    "bash -c \"grep 'rm -rf' .\"",
    # The '…'\''…' idiom parses as the single word it is.
    "grep 'it'\\''s rm -rf' file",
]

PLAIN_ALLOWED = [
    "git log --oneline -5",
    "make verify",
    "git status",
    "sh",  # a bare shell runs nothing deny-listed
    "bash script.sh",  # a shell on a file with no operation in sight
    "echo test | grep sh",  # grep's operand is not a piped-into shell
    "git commit -m 'first line\nsecond line'",
    "",
]


class TestDenied(unittest.TestCase):
    def assert_denied(self, command):
        result = verdict(command)
        self.assertEqual(
            result.returncode, DENY,
            "expected deny for %r; stderr: %s" % (command, result.stderr),
        )
        self.assertIn(b"block-destructive: denied", result.stderr)

    def test_true_positives(self):
        for command in TRUE_POSITIVES:
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_issue_40_fail_open_shapes(self):
        for command in ISSUE_40_REGRESSIONS:
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_review_found_fail_opens(self):
        for command in REVIEW_FOUND_FAIL_OPENS:
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_documented_surviving_false_positives(self):
        for command in DOCUMENTED_SURVIVING_FALSE_POSITIVES:
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_locale_independent_verdict(self):
        # Issue #40: under the previous grep bracket-expressions a high byte
        # before the operation flipped the verdict with the locale.
        text = b"cd \xffx && rm -rf y"
        for env in (
            {"LANG": "en_US.UTF-8", "PATH": "/usr/bin:/bin"},
            {"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
        ):
            with self.subTest(env=env):
                self.assertEqual(verdict(text, env=env).returncode, DENY)


class TestAllowed(unittest.TestCase):
    def assert_allowed(self, command):
        result = verdict(command)
        self.assertEqual(
            result.returncode, ALLOW,
            "expected allow for %r; stderr: %s" % (command, result.stderr),
        )

    def test_quoted_mentions_stay_allowed(self):
        for command in FALSE_POSITIVES_FIXED_BY_ADR_0015:
            with self.subTest(command=command):
                self.assert_allowed(command)

    def test_adr_0017_fixed_false_positives(self):
        for command in FALSE_POSITIVES_FIXED_BY_ADR_0017:
            with self.subTest(command=command):
                self.assert_allowed(command)

    def test_documented_blind_spots(self):
        # Pinned as allowed so that closing one is a deliberate change with a
        # documentation update, not a silent behaviour flip in either direction.
        for command in DOCUMENTED_BLIND_SPOTS:
            with self.subTest(command=command):
                self.assert_allowed(command)

    def test_plain_commands(self):
        for command in PLAIN_ALLOWED:
            with self.subTest(command=command):
                self.assert_allowed(command)


class TestFailurePosture(unittest.TestCase):
    def test_missing_python3_fails_closed(self):
        # With no python3 on PATH the guard must deny with a remedy, not
        # silently allow (exit 0) or error non-blockingly (exit 1).
        result = verdict(
            "git status", env={"PATH": "/nonexistent-for-guard-test"}
        )
        self.assertEqual(result.returncode, DENY)
        self.assertIn(b"python3", result.stderr)

    def _with_stub_python3(self, stub_body):
        """Verdict for a harmless command with a python3 stub first on PATH."""
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "python3"
            stub.write_text(stub_body)
            stub.chmod(0o755)
            return verdict("git status", env={"PATH": f"{tmp}:/usr/bin:/bin"})

    def test_interpreter_that_cannot_run_the_matcher_fails_closed(self):
        # `python3 -c ''` only proves an interpreter starts. One that then
        # fails on the matcher itself (a python2 shim, a stripped standard
        # library) exits 1 — which PreToolUse reads as a non-blocking error
        # and runs the command. The wrapper must turn it into a deny.
        result = self._with_stub_python3(
            '#!/bin/sh\n'
            '[ "$1" = "-c" ] && [ -z "$2" ] && exit 0\n'
            'echo "SyntaxError: invalid syntax" >&2\n'
            'exit 1\n'
        )
        self.assertEqual(result.returncode, DENY)
        self.assertIn(b"block-destructive: denied", result.stderr)

    def test_interpreter_exiting_zero_without_a_verdict_fails_closed(self):
        # Exit 0 alone is not an allow: the program prints a token on the
        # allow path, and an interpreter that never ran it cannot produce one.
        result = self._with_stub_python3('#!/bin/sh\nexit 0\n')
        self.assertEqual(result.returncode, DENY)
        self.assertIn(b"block-destructive: denied", result.stderr)

    def _guard_with_line(self, prefix, replacement):
        """Verdict helper for a guard copy with one deny-list line rewritten."""
        source = GUARD.read_text()
        patched = "\n".join(
            replacement if line.startswith(prefix) else line
            for line in source.split("\n")
        )
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        copy = Path(tmp) / "block-destructive.sh"
        copy.write_text(patched)
        return lambda command: subprocess.run(
            [SH, str(copy)], input=command.encode(), capture_output=True
        )

    def test_emptied_deny_list_fails_closed(self):
        # Any of the three lists failing to reach the matcher is damage, not a
        # licence to allow: the rule it feeds would silently stop existing.
        for prefix in ("operations=", "text_patterns=", "shells="):
            with self.subTest(variable=prefix):
                run = self._guard_with_line(prefix, prefix + "''")
                result = run("git status")
                self.assertEqual(result.returncode, DENY)
                self.assertIn(b"deny-list", result.stderr)

    def test_pre_tokenizer_shell_list_still_works(self):
        # A downstream repo that customised `shells` when it was an ERE group
        # keeps its parenthesised line through a copier update; the list must
        # not silently degrade to '(sh' and 'ash)'.
        run = self._guard_with_line("shells=", "shells='(sh|bash|dash|ash)'")
        for command in ("echo 'rm -rf /data' | sh", "sh -c 'rm -rf /tmp/x'"):
            with self.subTest(command=command):
                result = run(command)
                self.assertEqual(result.returncode, DENY)
                # An unopenable script also exits 2, so the verdict is the
                # exit code *plus* the guard's own message (ADR 0016).
                self.assertIn(b"block-destructive: denied", result.stderr)

    def test_runner_recursion_is_bounded(self):
        # Every runner token re-enters the matcher on the rest of the command,
        # so an unbounded walk costs exponentially and the hook times out —
        # which PreToolUse treats as a non-blocking error, i.e. as an allow.
        started = time.monotonic()
        self.assertEqual(verdict("ssh h " * 120 + "true").returncode, ALLOW)
        self.assertLess(time.monotonic() - started, 10)

    def test_exit_codes_are_binary(self):
        for command in TRUE_POSITIVES + FALSE_POSITIVES_FIXED_BY_ADR_0015:
            with self.subTest(command=command):
                self.assertIn(verdict(command).returncode, (ALLOW, DENY))


if __name__ == "__main__":
    unittest.main()
