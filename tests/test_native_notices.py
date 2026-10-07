"""Native user notices coexist with replacements and contain no document values."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from privacy_guard.claude_code.hook import run
from privacy_guard.claude_code.notices import PROTECTED_NOTICE, RESTORED_NOTICE, RESTORE_FAILED_NOTICE, notify
from privacy_guard.claude_code.responses import replace_tool_output, stop
from privacy_guard.claude_code.write_restoration import process_write_result
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from tests.fakes import RecordingNameService, ReversingCipher

VALUE = "alice.martin@example.com"


class NativeNoticeTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.vaults = VaultStore(Path(temporary.name), ReversingCipher())
        self.names = RecordingNameService()
        self.core = PrivacyCore(self.vaults.session("a"), self.names)

    def read(self, content):
        payload = {"session_id": "a", "hook_event_name": "PostToolUse", "tool_name": "Read",
                   "tool_input": {"file_path": "C:/sample.txt"}, "tool_response": {"content": content}}
        stdout = io.StringIO()
        code = run(io.StringIO(json.dumps(payload)), stdout, io.StringIO(),
                   SimpleNamespace(record=lambda *args: None), self.vaults, self.names)
        self.assertEqual(code, 0)
        self.assertNotIn(VALUE, stdout.getvalue())
        return json.loads(stdout.getvalue()) if stdout.getvalue() else {}

    def test_protected_document_has_one_native_notice_and_preserves_guidance(self):
        reply = self.read(VALUE)
        self.assertEqual(reply["systemMessage"], "Privacy Guard — sample.txt : 1 adresse e-mail pseudonymisée.")
        self.assertIn("updatedToolOutput", reply["hookSpecificOutput"])
        self.assertIn("additionalContext", reply["hookSpecificOutput"])

    def test_clean_and_already_protected_reads_do_not_claim_new_protection(self):
        self.assertEqual(self.read("Amount: 1200 EUR"), {})
        masked = self.read(VALUE)["hookSpecificOutput"]["updatedToolOutput"]["content"]
        self.assertNotIn("systemMessage", self.read(masked))

    def test_user_notice_preserves_native_stop_fields(self):
        reply = json.loads(notify(stop("Stopped"), "Generic notice").stdout)
        self.assertFalse(reply["continue"])
        self.assertEqual(reply["stopReason"], "Stopped")

    def test_notification_preserves_replacement_structure(self):
        output = {"stdout": "safe", "interrupted": False}
        reply = json.loads(notify(replace_tool_output(output), PROTECTED_NOTICE).stdout)
        self.assertEqual(reply["hookSpecificOutput"]["updatedToolOutput"], output)

    def test_write_notice_reports_restoration_success_and_failure(self):
        payload = {"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {}, "tool_response": {}}
        for changed, expected in ((True, RESTORED_NOTICE), (False, None), (RuntimeError(VALUE), RESTORE_FAILED_NOTICE)):
            def restore(*args):
                if isinstance(changed, Exception):
                    raise changed
                return changed

            reply = process_write_result(payload, self.core, SimpleNamespace(restore=restore))
            raw = json.loads(reply.stdout) if reply.stdout else {}
            self.assertNotIn(VALUE, reply.stdout)
            self.assertEqual(raw.get("systemMessage"), expected)
