import io
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from privacy_guard.claude_code.hook import handle, run
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from privacy_guard.service.cached_names import CachedNameDetector
from privacy_guard.service.channel import ServiceChannel
from privacy_guard.service.client import ServiceClient
from privacy_guard.service.server import serve
from tests.fakes import STRIPE_KEY, RecordingNameService, ReversingCipher


class CachedReadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.vaults = VaultStore(Path(self.temp.name), ReversingCipher())
        self.detector = RecordingNameService()
        self.cache = CachedNameDetector(self.detector)
        self.journal = SimpleNamespace(record=lambda event, tool: None)

    def tearDown(self):
        self.temp.cleanup()

    def read(self, path, text, session="session-a"):
        result = handle({"hook_event_name": "PostToolUse", "session_id": session,
                         "tool_name": "Read", "tool_input": {"file_path": path},
                         "tool_response": {"content": text}},
                        self.journal, self.vaults, self.cache)
        return json.loads(result.stdout)["hookSpecificOutput"]["updatedToolOutput"]["content"]

    def test_thousand_line_python_read_uses_rules_without_ner(self):
        source = "print('ready')\n" * 997 + (
            f"# Author: Jean Dupont\nEMAIL='jean.dupont@example.com'\nKEY='{STRIPE_KEY}'\n")
        for extension in ["py", "PY"]:
            protected = self.read("C:/src/app." + extension, source)
            self.assertNotIn("Jean Dupont", protected)
            self.assertNotIn("jean.dupont@example.com", protected)
            self.assertNotIn(STRIPE_KEY, protected)
            self.assertIn("⟦STRIPE_SECRET_KEY:REDACTED⟧", protected)
        self.assertEqual(self.detector.queried, [])

    def test_cache_hit_reprotects_and_restores_in_each_session(self):
        source = f"Nom : Jean Dupont\nEmail: jean.dupont@example.com\nKEY={STRIPE_KEY}"
        first = self.read("clients.txt", source)
        self.assertEqual(self.read("clients.txt", source), first)
        second = self.read("clients.txt", source, "session-b")
        self.assertNotEqual(first, second)
        personal = source.split("\nKEY=")[0]
        for session, protected in [("session-a", first), ("session-b", second)]:
            self.assertNotIn("Jean Dupont", protected)
            self.assertNotIn(STRIPE_KEY, protected)
            core = PrivacyCore(self.vaults.session(session), self.cache)
            self.assertEqual(core.restore(protected).split("\nKEY=")[0], personal)
            self.assertIn("⟦STRIPE_SECRET_KEY:REDACTED⟧", core.restore(protected))
        self.assertEqual(self.detector.queried, [source])

    def test_document_change_reanalyzes(self):
        self.read("clients.md", "Nom : Jean Dupont")
        changed = "Nom : Marie Martin"
        self.assertNotIn("Marie Martin", self.read("clients.md", changed))
        self.assertEqual(len(self.detector.queried), 2)

    def test_new_text_failure_masks_output_instead_of_using_old_findings(self):
        self.read("clients.txt", "Nom : Jean Dupont")
        payload = {"hook_event_name": "PostToolUse", "session_id": "session-a",
                   "tool_name": "Read", "tool_input": {"file_path": "clients.txt"},
                   "tool_response": {"content": "Nom : Marie Martin"}}
        stdout = io.StringIO()
        with patch.object(self.detector, "find_names", side_effect=RuntimeError("Unavailable")):
            run(io.StringIO(json.dumps(payload)), stdout, io.StringIO(),
                self.journal, self.vaults, self.cache)
        result = json.loads(stdout.getvalue())["hookSpecificOutput"]["updatedToolOutput"]
        self.assertIn("Output masked", result["content"])
        self.assertFalse(json.loads(stdout.getvalue())["continue"])
        self.assertNotIn("Marie Martin", stdout.getvalue())


class CachedServiceTest(unittest.TestCase):
    def test_real_channel_reuses_detection_and_reanalyzes_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            channel = ServiceChannel(Path(directory) / "run")
            detector = RecordingNameService()
            server = threading.Thread(target=serve, args=(channel, lambda: detector, 3600), daemon=True)
            server.start()
            client = ServiceClient(channel)
            try:
                deadline = time.monotonic() + 5
                while not client.is_ready():
                    if time.monotonic() > deadline:
                        self.fail("Test service did not start")
                    time.sleep(0.01)
                text = "Nom : Jean Dupont"
                first = client.find_names(text)
                self.assertEqual(client.find_names(text), first)
                self.assertEqual(len(detector.queried), 1)
                self.assertNotEqual(client.find_names("Nom : Marie Martin"), [])
                self.assertEqual(len(detector.queried), 2)
            finally:
                client.stop()
                server.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
