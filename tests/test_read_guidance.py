"""Read-time editing guidance through the real hook, before any Edit is attempted."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from privacy_guard.claude_code.hook import run
from privacy_guard.core.vault import VaultStore
from tests.fakes import RecordingNameService, ReversingCipher

EMAIL = "alice.martin@example.com"


class ReadGuidanceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.vaults = VaultStore(Path(self.temp.name), ReversingCipher())

    def call(self, response, path="C:/fictional/billing.md", tool="Read"):
        payload = {"hook_event_name": "PostToolUse", "session_id": "read-guidance",
                   "tool_name": tool, "tool_input": {"file_path": path}, "tool_response": response}
        stdout, stderr = io.StringIO(), io.StringIO()
        code = run(io.StringIO(json.dumps(payload)), stdout, stderr, Mock(), self.vaults, RecordingNameService())
        self.assertEqual((code, stderr.getvalue()), (0, ""))
        self.assertNotIn(EMAIL, stdout.getvalue())
        return json.loads(stdout.getvalue())["hookSpecificOutput"] if stdout.getvalue() else {}

    def test_protected_read_preserves_result_shape_and_stable_tokens_while_guiding_write(self):
        response = {"type": "text", "file": {"content": f"Email: {EMAIL}\nAmount: 1200 EUR", "numLines": 2}}
        first = self.call(response)
        second = self.call(response)
        self.assertEqual(first, second)
        self.assertEqual(first["updatedToolOutput"]["file"]["numLines"], 2)
        self.assertIn("1200 EUR", first["updatedToolOutput"]["file"]["content"])
        self.assertIn("use Write with session tokens", first["additionalContext"])
        self.assertIn("read the complete file", first["additionalContext"])
        self.assertNotIn("updatedInput", first)
        self.assertEqual(response["file"]["content"], f"Email: {EMAIL}\nAmount: 1200 EUR")

    def test_cached_read_gets_guidance_without_fabricating_a_document_body(self):
        response = {"type": "file_unchanged", "file": {"filePath": "C:/fictional/billing.md"}}
        result = self.call(response)
        self.assertIn("additionalContext", result)
        self.assertNotIn("updatedToolOutput", result)
        self.assertNotIn("updatedInput", result)

    def test_existing_tokens_receive_guidance_even_when_no_new_masking_is_needed(self):
        response = {"content": "\u27e6EMAIL:ABCDEF12\u27e7"}
        result = self.call(response)
        self.assertIn("additionalContext", result)
        self.assertNotIn("updatedToolOutput", result)

    def test_plain_document_reads_and_unsupported_formats_receive_no_guidance(self):
        self.assertEqual(self.call({"content": "Amount: 1200 EUR"}), {})
        result = self.call({"content": EMAIL}, path="C:/fictional/billing.docx")
        self.assertIn("updatedToolOutput", result)
        self.assertNotIn("additionalContext", result)

    def test_source_code_reads_are_guided_like_documents(self):
        result = self.call({"content": EMAIL}, path="C:/fictional/user_service.py")
        self.assertIn("additionalContext", result)

    def test_write_and_shell_outputs_keep_their_existing_behavior(self):
        for tool in ("Bash", "Write"):
            with self.subTest(tool=tool):
                result = self.call({"content": EMAIL}, tool=tool)
                self.assertIn("updatedToolOutput", result)
                self.assertNotIn("additionalContext", result)
