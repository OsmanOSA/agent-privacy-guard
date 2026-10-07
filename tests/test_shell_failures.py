import json
import subprocess
import sys
import unittest

from privacy_guard.claude_code.responses import EXIT_ALLOW, PRE_TOOL_USE
from privacy_guard.claude_code.shell_failures import FAILED_MARKER, before_shell, route_shell_failures
from tests.native_shell import native_bash

POWERSHELL_TRAILER = "\nWrite-Output ''"

TRAILER = f' || echo "{FAILED_MARKER}"'


def routed(command: str) -> str:
    return route_shell_failures({"command": command})["command"]


class RouteShellFailuresTest(unittest.TestCase):
    def test_single_line_command_reports_failure_and_ends_successfully(self):
        self.assertEqual(routed("npm test"), "npm test" + TRAILER)

    def test_multi_line_command_reports_failure_after_its_last_line(self):
        self.assertEqual(routed("cd app\nnpm test"), "cd app\nnpm test" + TRAILER)

    def test_last_line_that_could_swallow_the_trailer_gets_a_separate_line(self):
        for command in ("ls # comment", "cat <<'X'\nbody\nX", "sleep 5 &", "make;"):
            with self.subTest(command=command):
                self.assertEqual(routed(command), command + "\ntrue")

    def test_incomplete_command_is_left_untouched(self):
        # Appending would complete it with a new meaning (npm test | true).
        for command in ("echo a \\", "npm test |", "make &&", "make ||"):
            with self.subTest(command=command):
                self.assertIsNone(route_shell_failures({"command": command}))

    def test_other_arguments_are_preserved(self):
        arguments = {"command": "pytest", "timeout": 5000, "description": "Run tests"}
        self.assertEqual(route_shell_failures(arguments), {**arguments, "command": "pytest" + TRAILER})

    def test_unusable_arguments_are_left_to_claude_code(self):
        for arguments in (None, {}, {"command": 3}, {"command": "  "}):
            with self.subTest(arguments=arguments):
                self.assertIsNone(route_shell_failures(arguments))


class PowerShellRouteTest(unittest.TestCase):
    def routed(self, command):
        return route_shell_failures({"command": command}, "PowerShell")["command"]

    def test_every_command_ends_with_a_successful_statement(self):
        for command in ("Get-Content notes.md", "npm test # run", "Get-Content a; Get-Content b"):
            with self.subTest(command=command):
                self.assertEqual(self.routed(command), command + POWERSHELL_TRAILER)

    def test_incomplete_command_is_left_untouched(self):
        for command in ("Get-Content a `", "Get-Content a |", "npm test &&"):
            with self.subTest(command=command):
                self.assertIsNone(route_shell_failures({"command": command}, "PowerShell"))

    def test_other_tools_are_not_rewritten(self):
        self.assertIsNone(route_shell_failures({"command": "x"}, "Monitor"))

    @unittest.skipUnless(sys.platform == "win32", "Windows PowerShell")
    def test_failure_ends_with_status_zero_and_keeps_its_error_text(self):
        command = self.routed("Get-Content missing-file-for-test.txt")
        result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                                capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"missing-file-for-test", result.stderr + result.stdout)


class BeforeShellTest(unittest.TestCase):
    def test_returns_updated_input_without_granting_permission(self):
        result = before_shell({"tool_name": "Bash", "tool_input": {"command": "false"}})
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(result.exit_code, EXIT_ALLOW)
        self.assertEqual(output["hookEventName"], PRE_TOOL_USE)
        self.assertNotIn("permissionDecision", output)
        self.assertEqual(output["updatedInput"]["command"], "false" + TRAILER)

    def test_unroutable_command_is_allowed_unchanged(self):
        self.assertEqual(before_shell({"tool_name": "Bash", "tool_input": {"command": "echo a \\"}}).stdout, "")


class ShellExecutionTest(unittest.TestCase):
    """The trailer must turn failures into status 0 without changing what the command does."""

    def run_bash(self, command: str) -> subprocess.CompletedProcess:
        return subprocess.run([native_bash(), "-c", routed(command)], capture_output=True, text=True, timeout=30)

    def test_failures_end_with_status_zero_and_keep_their_output(self):
        for command in ("echo out; false", "ls missing-file-for-test", "printf 'a\\nb' | grep zzz",
                        "if true; then\n  false\nfi"):
            with self.subTest(command=command):
                result = self.run_bash(command)
                self.assertEqual(result.returncode, 0)
                self.assertIn(FAILED_MARKER, result.stdout)

    def test_success_is_unchanged(self):
        result = self.run_bash("echo ok")
        self.assertEqual((result.returncode, result.stdout), (0, "ok\n"))

    def test_heredoc_and_comment_still_work(self):
        self.assertEqual(self.run_bash("cat <<'X'\nbody\nX").stdout, "body\n")
        self.assertEqual(self.run_bash("echo kept # comment").stdout, "kept\n")
        self.assertEqual(self.run_bash("false # comment").returncode, 0)


if __name__ == "__main__":
    unittest.main()
