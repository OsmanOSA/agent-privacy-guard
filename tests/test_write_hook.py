"""Automatic post-Write cycles and content-free notices through the real hook interface."""

import io
import json
import sys
import unittest
from unittest.mock import Mock

from privacy_guard.claude_code.hook import run
from privacy_guard.claude_code.write_restoration import process_write_result
from tests.fakes import RecordingNameService
from tests.written_file_fixtures import EMAIL, NAME, ORIGINAL, WrittenFileTestCase
from tests.vault_storage import corrupt_records


class Journal:
    def __init__(self):
        self.events = []

    def record(self, event, tool):
        self.events.append((event, tool))


@unittest.skipUnless(sys.platform == "win32", "Native Windows hook")
class WriteHookTest(WrittenFileTestCase):
    def setUp(self):
        super().setUp()
        self.journal = Journal()
        self.names = RecordingNameService()

    def call(self, event, tool, args, response=None, session="a"):
        payload = {"hook_event_name": event, "session_id": session, "tool_name": tool,
                   "tool_input": args, "tool_response": response}
        stdout, stderr = io.StringIO(), io.StringIO()
        code = run(io.StringIO(json.dumps(payload)), stdout, stderr, self.journal, self.vaults, self.names)
        self.assertEqual((code, stderr.getvalue()), (0, ""))
        self.assertNotIn(EMAIL, stdout.getvalue())
        self.assertNotIn(NAME, stdout.getvalue())
        return json.loads(stdout.getvalue())["hookSpecificOutput"] if stdout.getvalue() else {}

    def test_three_automatic_write_reread_cycles_preserve_tokens(self):
        current = self.masked
        for index in range(3):
            target = self.home / f"result-{index}.txt"
            args = {"file_path": str(target), "content": current}
            before = self.call("PreToolUse", "Write", args)
            self.assertEqual(before, {})
            self.assertFalse(target.exists(), "PreToolUse must not write before permission")
            # Simulate the authorized tool, then process its successful result.
            target.write_text(current, encoding="utf-8", newline="")
            after = self.call("PostToolUse", "Write", args, {"filePath": str(target), "type": "create"})
            self.assertNotIn("updatedInput", after)
            self.assertIn("restored", after["additionalContext"])
            self.assertEqual(target.read_text(encoding="utf-8"), ORIGINAL)
            reread = self.call("PostToolUse", "Read", {"file_path": str(target)},
                               {"content": target.read_text(encoding="utf-8")})
            current = reread["updatedToolOutput"]["content"]
            self.assertEqual(current, self.masked)
        self.assertNotIn(EMAIL, repr(self.journal.events))
        self.assertNotIn(NAME, repr(self.journal.events))

    def test_external_markers_survive_read_write_restore_and_reread(self):
        original = ORIGINAL + 'Marker: [PERSON_001]\nEmail marker: [EMAIL_001]\n'
        target = self.home / 'external-markers.md'
        masked = self.call('PostToolUse', 'Read', {'file_path': str(target)},
                           {'content': original})['updatedToolOutput']['content']
        self.assertIn('[PERSON_001]', masked)
        self.assertIn('[EMAIL_001]', masked)
        self.assertIn('⟦PERSON_NAME:', masked)
        self.assertIn('⟦EMAIL:', masked)
        target.write_text(masked, encoding='utf-8', newline='')
        args = {'file_path': str(target), 'content': masked}
        self.call('PostToolUse', 'Write', args, {'filePath': str(target), 'type': 'create'})
        self.assertEqual(target.read_text(encoding='utf-8'), original)
        reread = self.call('PostToolUse', 'Read', {'file_path': str(target)},
                           {'content': original})['updatedToolOutput']['content']
        self.assertEqual(reread, masked)

    def test_write_result_remains_protected_when_it_contains_originals(self):
        path, args = self.written()
        result = self.call("PostToolUse", "Write", args,
                           {"filePath": str(path), "type": "update", "content": ORIGINAL})
        self.assertEqual(set(result["updatedToolOutput"]), {"filePath", "type", "content"})
        self.assertEqual(result["updatedToolOutput"]["content"], self.masked)
        self.assertEqual(path.read_text(encoding="utf-8"), ORIGINAL)

    def test_content_race_returns_generic_failure_and_preserves_file(self):
        path, args = self.written()
        path.write_text("competing", encoding="utf-8")
        result = self.call("PostToolUse", "Write", args, {"filePath": str(path), "type": "create"})
        self.assertIn("failed", result["additionalContext"])
        self.assertEqual(path.read_text(encoding="utf-8"), "competing")

    def test_no_restoration_on_pretool_failure_edit_shell_or_remote_events(self):
        for event, tool in (("PreToolUse", "Write"), ("PostToolUseFailure", "Write"),
                            ("PostToolUse", "Edit"), ("PostToolUse", "Bash"),
                            ("PostToolUse", "Agent"), ("PostToolUse", "mcp__remote__send")):
            with self.subTest(event=event, tool=tool):
                writer = Mock()
                payload = {"hook_event_name": event, "tool_name": tool, "tool_response": {}, "tool_input": {}}
                process_write_result(payload, self.core, writer)
                writer.restore.assert_not_called()

    def test_unsupported_write_remains_masked_without_an_egress_side_effect(self):
        path, args = self.written(name="result.xlsx")
        result = self.call("PostToolUse", "Write", args, {"filePath": str(path), "type": "create"})
        self.assertEqual(result, {})
        self.assertEqual(path.read_text(encoding="utf-8"), self.masked)

    def test_corrupted_vault_returns_generic_failure_and_keeps_tokens(self):
        path, args = self.written()
        corrupt_records(self.home / "vault" / "a")
        stdout = io.StringIO()
        payload = dict(hook_event_name='PostToolUse', session_id='a', tool_name='Write',
                       tool_input=args, tool_response={'filePath': str(path), 'type': 'create'})
        code = run(io.StringIO(json.dumps(payload)), stdout, io.StringIO(), self.journal, self.vaults, self.names)
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(stdout.getvalue())['continue'])
        self.assertNotIn(EMAIL, stdout.getvalue())
        self.assertEqual(path.read_text(encoding="utf-8"), self.masked)
