import json
import unittest

from privacy_guard.claude_code.shell_exits import ends_shell_early
from privacy_guard.claude_code.shell_failures import before_shell


class BashEarlyExitTest(unittest.TestCase):
    def test_constructs_that_end_the_shell_before_the_trailer(self):
        for command in ("cat notes.md; exit 3", "exit", "make || exit 1", "if x; then exit 2; fi",
                        "set -e\nnpm test", "set -euo pipefail; ls", "set -o errexit", "exec npm test",
                        "(cd app && exit 4)"):
            with self.subTest(command=command):
                self.assertTrue(ends_shell_early(command, "Bash"))

    def test_harmless_mentions_are_allowed(self):
        for command in ("exit 0", "echo done; exit 0", "grep -n exit app.sh", "git commit -m 'fix exit code'",
                        'echo "set -e"', "cat <<'EOF' > run.sh\nset -e\nexit 1\nEOF\nchmod +x run.sh",
                        "set +e", "set -x", "exec >log.txt 2>&1", "ls  # exit 1 later", "npm run exit-test"):
            with self.subTest(command=command):
                self.assertFalse(ends_shell_early(command, "Bash"))


class PowerShellEarlyExitTest(unittest.TestCase):
    def test_constructs_that_end_the_script_before_the_trailer(self):
        for command in ("Get-Content a; exit 1", "if ($x) { exit 2 }", "throw 'missing'",
                        "Get-Content a -ErrorAction Stop", "Get-Content a -ea stop",
                        "$ErrorActionPreference = 'Stop'\nGet-Content a"):
            with self.subTest(command=command):
                self.assertTrue(ends_shell_early(command, "PowerShell"))

    def test_harmless_mentions_are_allowed(self):
        for command in ("exit 0", "Select-String exit a.ps1", "Write-Output 'throw'",
                        "Get-Content a -ErrorAction SilentlyContinue", "@'\nexit 1\n'@ | Set-Content s.ps1",
                        "Get-Content a # throw later"):
            with self.subTest(command=command):
                self.assertFalse(ends_shell_early(command, "PowerShell"))


class BeforeShellBlockTest(unittest.TestCase):
    def test_early_exit_is_refused_with_a_rewrite_instruction(self):
        result = before_shell({"tool_name": "Bash", "tool_input": {"command": "cat notes.md; exit 3"}})
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual((result.exit_code, output["permissionDecision"]), (0, "deny"))
        self.assertIn("|| true", output["permissionDecisionReason"])

    def test_ordinary_command_is_still_rewritten(self):
        result = before_shell({"tool_name": "PowerShell", "tool_input": {"command": "Get-Content a"}})
        self.assertIn("updatedInput", json.loads(result.stdout)["hookSpecificOutput"])


if __name__ == "__main__":
    unittest.main()
