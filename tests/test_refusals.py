import json
import re
import unittest

from privacy_guard.claude_code import registration
from privacy_guard.claude_code.hook import fail_closed
from privacy_guard.claude_code.responses import EXIT_ALLOW, EXIT_BLOCK, deny


def deny_output(result):
    return json.loads(result.stdout)["hookSpecificOutput"]


class DenyShapeTest(unittest.TestCase):
    """A malformed deny is a non-blocking error for Claude Code: the shape must be exact."""

    def test_deny_is_the_documented_pre_tool_use_decision(self):
        result = deny("Privacy Guard: refused.")
        self.assertEqual((result.exit_code, result.stderr), (EXIT_ALLOW, ""))
        self.assertEqual(json.loads(result.stdout), {"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": "Privacy Guard: refused."}})

    def test_internal_failure_refuses_tools_and_blocks_other_events(self):
        self.assertEqual(deny_output(fail_closed("PreToolUse"))["permissionDecision"], "deny")
        for event in ("SessionStart", "SessionEnd", "unknown"):
            with self.subTest(event=event):
                self.assertEqual(fail_closed(event).exit_code, EXIT_BLOCK)

    def test_guard_refusal_is_the_same_json_without_any_path(self):
        guard = registration.guard_handler("C:/Users/u/runtime/python.exe", "C:/Users/u/.privacy-guard/app")
        literal = re.search(r"WriteLine\('(.*?)'\)", guard["command"]).group(1).replace("''", "'")
        output = json.loads(literal)["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertNotIn("C:/Users", output["permissionDecisionReason"])


if __name__ == "__main__":
    unittest.main()
