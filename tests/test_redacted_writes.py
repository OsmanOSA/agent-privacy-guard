"""Writes of redaction markers are refused through the hook interface, without file or vault access."""

import io
import json
import unittest
from unittest.mock import Mock

from privacy_guard.claude_code.hook import run
from tests.fakes import refusal

REDACTION = "\u27e6GITHUB_TOKEN:REDACTED\u27e7"
TOKEN = "\u27e6EMAIL:ABCDEF12\u27e7"


class RedactedWritesTest(unittest.TestCase):
    def call(self, tool, args):
        vaults, names, journal = Mock(), Mock(), Mock()
        payload = {"hook_event_name": "PreToolUse", "session_id": "redacted-writes",
                   "tool_name": tool, "tool_input": args}
        stdout, stderr = io.StringIO(), io.StringIO()
        code = run(io.StringIO(json.dumps(payload)), stdout, stderr, journal, vaults, names)
        vaults.session.assert_not_called()
        return refusal(code, stdout.getvalue(), stderr.getvalue())

    def test_every_file_tool_that_would_write_a_redaction_is_refused(self):
        cases = {
            "Write": {"file_path": "C:/fictional/.env", "content": f"APP_ENV=prod\nGITHUB_TOKEN={REDACTION}\n"},
            "Edit": {"file_path": "C:/fictional/app.bin", "old_string": "a", "new_string": REDACTION},
            "MultiEdit": {"file_path": "C:/fictional/app.py",
                          "edits": [{"old_string": "a", "new_string": f"KEY = '{REDACTION}'"}]},
            "NotebookEdit": {"notebook_path": "C:/fictional/n.ipynb", "new_source": REDACTION},
        }
        for tool, args in cases.items():
            with self.subTest(tool=tool):
                reason = self.call(tool, args)
                self.assertIsNotNone(reason)
                self.assertIn("secret", reason)
                self.assertNotIn("GITHUB_TOKEN", reason)
                self.assertNotIn("C:/fictional", reason)

    def test_redaction_only_in_old_string_is_left_to_the_edit_policy(self):
        # The marker is absent from disk, so such an Edit cannot overwrite the secret.
        args = {"file_path": "C:/fictional/app.bin", "old_string": REDACTION, "new_string": "x"}
        self.assertIsNone(self.call("Edit", args))

    def test_reversible_tokens_and_plain_content_are_allowed(self):
        for content in (f"CONTACT = '{TOKEN}'\n", "APP_ENV=prod\n"):
            with self.subTest(content=content):
                self.assertIsNone(self.call("Write", {"file_path": "C:/fictional/app.py", "content": content}))


if __name__ == "__main__":
    unittest.main()
