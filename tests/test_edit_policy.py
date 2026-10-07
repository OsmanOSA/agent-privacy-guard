"""Pre-Edit policy through the hook interface, without file or vault access."""

import io
import json
import unittest
from unittest.mock import Mock

from privacy_guard.claude_code.hook import run

TOKEN = "\u27e6EMAIL:1234ABCD\u27e7"
REDACTION = "\u27e6STRIPE_KEY:REDACTED\u27e7"


class EditPolicyTest(unittest.TestCase):
    def call(self, args, tool="Edit"):
        vaults, names, journal = Mock(), Mock(), Mock()
        payload = {"hook_event_name": "PreToolUse", "session_id": "edit-policy",
                   "tool_name": tool, "tool_input": args}
        stdout, stderr = io.StringIO(), io.StringIO()
        code = run(io.StringIO(json.dumps(payload)), stdout, stderr, journal, vaults, names)
        vaults.session.assert_not_called()
        names.find_names.assert_not_called()
        self.assertEqual(stdout.getvalue(), "", "Never return originals or changed arguments")
        return code, stderr.getvalue()

    def args(self, old="pending", new="paid", extension=".md"):
        return {"file_path": "C:/fictional/result" + extension,
                "old_string": old, "new_string": new, "replace_all": False}

    def test_unknown_token_in_old_string_returns_content_free_write_guidance(self):
        code, reason = self.call(self.args(old=TOKEN))
        self.assertEqual(code, 2)
        self.assertIn("Read the complete file", reason)
        self.assertIn("Write", reason)
        self.assertNotIn(TOKEN, reason)
        self.assertNotIn("C:/fictional", reason)

    def test_new_string_placeholders_and_redactions_take_the_same_route(self):
        for token in (TOKEN, REDACTION, "\u27e6PERSON_NAME:ABCDEF12\u27e7"):
            with self.subTest(token=token):
                self.assertEqual(self.call(self.args(new=token))[0], 2)

    def test_all_supported_document_extensions_are_case_insensitive(self):
        for extension in (".txt", ".md", ".markdown", ".csv", ".MD"):
            with self.subTest(extension=extension):
                self.assertEqual(self.call(self.args(old=TOKEN, extension=extension))[0], 2)

    def test_nonpersonal_status_amount_and_prose_edits_have_no_permission_decision(self):
        for old, new in (("pending", "paid"), ("1200 EUR", "1300 EUR"), ("## Total", "## Summary")):
            with self.subTest(old=old):
                self.assertEqual(self.call(self.args(old, new)), (0, ""))

    def test_write_and_other_tools_are_unchanged(self):
        for tool in ("Write", "Bash", "MultiEdit", "mcp__remote__Edit"):
            with self.subTest(tool=tool):
                self.assertEqual(self.call(self.args(old=TOKEN), tool), (0, ""))

    def test_formats_without_automatic_restoration_are_unchanged(self):
        for extension in (".py", ".json", ".tsv", ".html"):
            with self.subTest(extension=extension):
                self.assertEqual(self.call(self.args(old=TOKEN, extension=extension)), (0, ""))

    def test_missing_or_nonstring_arguments_are_left_to_tool_validation(self):
        for args in (None, [], {}, {"file_path": None}, self.args(old=None, new=12)):
            with self.subTest(args=args):
                self.assertEqual(self.call(args), (0, ""))
