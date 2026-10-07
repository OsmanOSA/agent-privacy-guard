"""Schema-preserving failure responses and native stop on sensitive tool errors."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from privacy_guard.claude_code.hook import run
from privacy_guard.claude_code.tool_failures import inspection_failed
from privacy_guard.core.vault import VaultStore
from tests.fakes import RecordingNameService, ReversingCipher

VALUE = "alice.martin@example.com"


class HookFailureTest(unittest.TestCase):
    def call(self, payload, broken=True):
        def record(*args):
            if broken:
                raise OSError(VALUE)

        with tempfile.TemporaryDirectory() as directory:
            stdout, stderr = io.StringIO(), io.StringIO()
            code = run(io.StringIO(json.dumps({"session_id": "a", **payload})), stdout, stderr,
                       SimpleNamespace(record=record), VaultStore(Path(directory), ReversingCipher()),
                       RecordingNameService())
        raw = stdout.getvalue()
        self.assertNotIn(VALUE, raw + stderr.getvalue())
        return code, json.loads(raw) if raw else {}

    def failure(self, tool, output):
        code, reply = self.call({"hook_event_name": "PostToolUse", "tool_name": tool, "tool_response": output})
        self.assertEqual(code, 0)
        self.assertFalse(reply["continue"])
        self.assertEqual(reply["stopReason"], reply["systemMessage"])
        return reply

    def test_bash_failure_uses_native_object_instead_of_plain_string(self):
        reply = self.failure("Bash", {"stdout": VALUE, "stderr": VALUE, "isImage": False, "interrupted": False})
        output = reply["hookSpecificOutput"]["updatedToolOutput"]
        self.assertEqual(set(output), {"stdout", "stderr", "isImage", "interrupted"})
        self.assertIsInstance(output["stdout"], str)
        self.assertIsInstance(output["stderr"], str)
        self.assertIs(type(output["isImage"]), bool)
        self.assertIs(type(output["interrupted"]), bool)

    def test_native_text_read_keeps_discriminator_and_numeric_metadata(self):
        original = {"type": "text", "file": {"filePath": "C:/" + VALUE,
                    "content": VALUE, "numLines": 1, "startLine": 1, "totalLines": 1}}
        reply = self.failure("Read", original)
        output = reply["hookSpecificOutput"]["updatedToolOutput"]
        self.assertEqual(output["type"], "text")
        self.assertEqual(set(output["file"]), set(original["file"]))
        self.assertEqual(output["file"]["totalLines"], 1)
        self.assertEqual(original["file"]["content"], VALUE)

    def test_search_failures_keep_mode_and_remove_matching_paths(self):
        for tool, original in (("Grep", {"mode": "content", "content": VALUE,
                               "filenames": [VALUE], "numFiles": 1, "numLines": 1}),
                              ("Glob", {"filenames": [VALUE], "numFiles": 1, "durationMs": 1})):
            reply = self.failure(tool, original)
            output = reply["hookSpecificOutput"]["updatedToolOutput"]
            self.assertEqual(set(output), set(original))
            self.assertEqual(output["filenames"], [])
            if tool == "Grep":
                self.assertEqual(output["mode"], "content")

    def test_mcp_failure_returns_an_error_text_block(self):
        reply = self.failure("mcp__example__read", {VALUE: VALUE})
        output = reply["hookSpecificOutput"]["updatedToolOutput"]
        self.assertTrue(output["isError"])
        self.assertEqual(output["content"][0]["type"], "text")

    def test_unknown_or_binary_shapes_stop_without_an_invalid_replacement(self):
        cases = [("Read", {"type": "image", "file": VALUE}),
                 ("Read", {VALUE: VALUE}), ("OtherTool", VALUE),
                 ("Grep", {"mode": [], "filenames": [VALUE]}),
                 ("Glob", {"filenames": [VALUE], "extra": VALUE})]
        for tool, original in cases:
            with self.subTest(tool=tool, output=original):
                self.assertNotIn("hookSpecificOutput", self.failure(tool, original))

    def test_failed_tool_with_sensitive_error_stops_without_echoing_error(self):
        code, reply = self.call({"hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
                                 "error": "Command failed for " + VALUE}, broken=False)
        self.assertEqual(code, 0)
        self.assertFalse(reply["continue"])
        self.assertNotIn("hookSpecificOutput", reply)

    def test_clean_failed_tool_error_can_continue(self):
        self.assertEqual(self.call({"hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
                                    "error": "Exit code 1: command unavailable"}, broken=False), (0, {}))

    def test_uninspectable_failed_tool_error_stops(self):
        _, reply = self.call({"hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
                              "error": {"unexpected": VALUE}}, broken=False)
        self.assertFalse(reply["continue"])

    def test_missing_event_payload_still_produces_a_stop(self):
        reply = json.loads(inspection_failed("PostToolUse", None).stdout)
        self.assertFalse(reply["continue"])
        self.assertNotIn("hookSpecificOutput", reply)

    def test_malformed_event_name_does_not_break_the_failure_handler(self):
        code, reply = self.call({"hook_event_name": {"unexpected": VALUE}})
        self.assertEqual((code, reply["hookSpecificOutput"]["permissionDecision"]), (0, "deny"))
