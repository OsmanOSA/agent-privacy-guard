"""Prove the restored-file Edit mismatch and the existing Write recovery cycle."""

import io
import json
import sys
import unittest
from unittest.mock import Mock

from privacy_guard.claude_code.hook import run
from tests.fakes import RecordingNameService
from tests.written_file_fixtures import EMAIL, NAME, ORIGINAL, WrittenFileTestCase


@unittest.skipUnless(sys.platform == "win32", "Native Windows restoration")
class EditFallbackTest(WrittenFileTestCase):
    def call(self, event, tool, args, response=None):
        payload = {"hook_event_name": event, "session_id": "a", "tool_name": tool,
                   "tool_input": args, "tool_response": response}
        stdout, stderr = io.StringIO(), io.StringIO()
        code = run(io.StringIO(json.dumps(payload)), stdout, stderr, Mock(),
                   self.vaults, RecordingNameService())
        output = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn(EMAIL, output)
        self.assertNotIn(NAME, output)
        result = json.loads(stdout.getvalue())["hookSpecificOutput"] if stdout.getvalue() else {}
        return code, result, stderr.getvalue()

    def test_token_edit_is_refused_then_write_changes_amount_and_restores_personal_values(self):
        path, write_args = self.written()
        code, post, _ = self.call("PostToolUse", "Write", write_args, {"filePath": str(path), "type": "create"})
        self.assertEqual(code, 0)
        self.assertIn("restored", post["additionalContext"])
        self.assertEqual(path.read_text(encoding="utf-8"), ORIGINAL)
        code, reread, _ = self.call("PostToolUse", "Read", {"file_path": str(path)}, {"content": ORIGINAL})
        masked = reread["updatedToolOutput"]["content"]
        changed = masked.replace("1200 EUR", "1300 EUR")
        self.assertEqual(path.read_text(encoding="utf-8").count(masked), 0,
                         "The token-containing old string cannot match the restored file")
        args = {"file_path": str(path), "old_string": masked, "new_string": changed}
        code, result, _ = self.call("PreToolUse", "Edit", args)
        self.assertEqual((code, result["permissionDecision"]), (0, "deny"))
        self.assertIn("Write", result["permissionDecisionReason"])
        self.assertEqual(path.read_text(encoding="utf-8"), ORIGINAL, "Refusal must not touch the file")
        write_args = {"file_path": str(path), "content": changed}
        self.assertEqual(self.call("PreToolUse", "Write", write_args), (0, {}, ""))
        path.write_text(changed, encoding="utf-8", newline="")
        code, post, _ = self.call("PostToolUse", "Write", write_args, {"filePath": str(path), "type": "update"})
        self.assertEqual(code, 0)
        self.assertIn("restored", post["additionalContext"])
        expected = ORIGINAL.replace("1200 EUR", "1300 EUR")
        self.assertEqual(path.read_text(encoding="utf-8"), expected)
        code, final, _ = self.call("PostToolUse", "Read", {"file_path": str(path)}, {"content": expected})
        self.assertEqual(code, 0)
        self.assertEqual(final["updatedToolOutput"]["content"], changed)

    def test_status_only_edit_can_run_without_replacing_original_personal_values(self):
        path = self.home / "status.md"
        initial = ORIGINAL + "Status: pending\n"
        path.write_text(initial, encoding="utf-8")
        args = {"file_path": str(path), "old_string": "pending", "new_string": "paid"}
        self.assertEqual(self.call("PreToolUse", "Edit", args), (0, {}, ""))
        updated = initial.replace("pending", "paid")
        path.write_text(updated, encoding="utf-8")
        code, post, _ = self.call("PostToolUse", "Edit", args, {"content": updated})
        self.assertEqual(code, 0)
        self.assertEqual(path.read_text(encoding="utf-8"), updated)
        self.assertEqual(post["updatedToolOutput"]["content"], self.core.protect(updated))
