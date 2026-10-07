"""Real-file cycles through the local exporter and hook; no live model calls."""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from privacy_guard.claude_code.hook import run
from privacy_guard.core.cipher import default_cipher
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from privacy_guard.exports.csv_writer import CsvWriter
from privacy_guard.exports.policy import CsvExportPolicy
from tests.fakes import RecordingNameService, STRIPE_KEY

EMAIL = "alice.martin@example.com"
NAME = "Alice Martin"
ORIGINAL = f"name,email,amount\nNom : {NAME},{EMAIL},1200\n"


class ContentFreeJournal:
    def __init__(self):
        self.events = []

    def record(self, event, tool):
        self.events.append((event, tool))


@unittest.skipUnless(sys.platform == "win32", "Native Windows cycle")
class ProtectionCycleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve()
        self.root = self.home / "exports"
        self.root.mkdir()
        self.vaults = VaultStore(self.home / "vault", default_cipher())
        self.names = RecordingNameService()
        self.journal = ContentFreeJournal()
        self.writer = CsvWriter(CsvExportPolicy(self.root))

    def tearDown(self):
        self.tmp.cleanup()

    def read_through_hook(self, path, session="a"):
        payload = {"hook_event_name": "PostToolUse", "session_id": session, "tool_name": "Read",
                   "tool_input": {"file_path": str(path)},
                   "tool_response": {"content": path.read_text(encoding="utf-8")}}
        stdout, stderr = io.StringIO(), io.StringIO()
        code = run(io.StringIO(json.dumps(payload)), stdout, stderr, self.journal, self.vaults, self.names)
        self.assertEqual((code, stderr.getvalue()), (0, ""))
        self.assertNotIn(EMAIL, stdout.getvalue())
        self.assertNotIn(NAME, stdout.getvalue())
        return json.loads(stdout.getvalue())["hookSpecificOutput"]["updatedToolOutput"]["content"]

    def restore(self, session="a"):
        return PrivacyCore(self.vaults.session(session), HeuristicNameDetector()).restore

    def test_three_read_export_reread_cycles_keep_the_same_session_tokens(self):
        source = self.home / "source.csv"
        source.write_text(ORIGINAL, encoding="utf-8")
        masked = self.read_through_hook(source)
        self.assertIn("⟦PERSON_NAME:", masked)
        self.assertIn("⟦EMAIL:", masked)
        for number in range(3):
            filename = f"cycle-{number}.csv"
            self.writer.write(filename, masked, self.restore())
            written = self.root / filename
            self.assertEqual(written.read_text(encoding="utf-8"), ORIGINAL)
            reread = self.read_through_hook(written)
            self.assertEqual(reread.replace("\r\n", "\n"), masked.replace("\r\n", "\n"))
            masked = reread
        self.assertNotIn(EMAIL, repr(self.journal.events))
        self.assertNotIn(NAME, repr(self.journal.events))

    def test_another_session_reprotects_the_restored_file_with_its_own_tokens(self):
        source = self.home / "source.csv"
        source.write_text(ORIGINAL, encoding="utf-8")
        masked = self.read_through_hook(source)
        self.writer.write("result.csv", masked, self.restore())
        second = self.read_through_hook(self.root / "result.csv", "b")
        self.assertNotEqual(second, masked)
        self.assertEqual(self.restore("b")(second).replace("\r\n", "\n"), ORIGINAL)

    def test_secrets_remain_redacted_after_export_and_reread(self):
        source = self.home / "source.csv"
        source.write_text(f"credential\n{STRIPE_KEY}\n", encoding="utf-8")
        masked = self.read_through_hook(source)
        self.writer.write("result.csv", masked, self.restore())
        written = (self.root / "result.csv").read_text(encoding="utf-8")
        self.assertNotIn(STRIPE_KEY, written)
        self.assertIn("⟦STRIPE_SECRET_KEY:REDACTED⟧", written)
        payload = {"hook_event_name": "PostToolUse", "session_id": "a", "tool_name": "Read",
                   "tool_input": {"file_path": str(self.root / "result.csv")}, "tool_response": {"content": written}}
        stdout = io.StringIO()
        code = run(io.StringIO(json.dumps(payload)), stdout, io.StringIO(), self.journal, self.vaults, self.names)
        self.assertEqual(code, 0)
        response = json.loads(stdout.getvalue())["hookSpecificOutput"]
        self.assertNotIn("updatedToolOutput", response)
        self.assertIn("additionalContext", response)
        self.assertNotIn(STRIPE_KEY, stdout.getvalue())
