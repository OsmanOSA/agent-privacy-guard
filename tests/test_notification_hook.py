"""Optional notification failures must preserve actual hook protection."""

import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from privacy_guard.claude_code.hook import run
from privacy_guard.core.vault import VaultStore
from privacy_guard.journal import EventJournal
from privacy_guard.notifications.client import NotificationJournal, desktop_journal
from privacy_guard.notifications.config import configure, read_mode
from privacy_guard.notifications.queue import NotificationQueue
from privacy_guard.notifications.worker import deliver, banner_text
from privacy_guard.protection_summary import ProtectionSummary
from tests.fakes import RecordingNameService, ReversingCipher


class NotificationHookTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.directory = self.root / "notifications"
        configure(self.directory, "background")
        self.capture = Mock(return_value=None)
        self.launch = Mock()
        self.journal = NotificationJournal(EventJournal(self.root / "logs/guard.log"),
                                           self.directory, self.capture, self.launch)
        self.vaults = VaultStore(self.root / "vault", ReversingCipher())

    def call(self, content="alice@example.com", event="PostToolUse"):
        payload = {"hook_event_name": event, "session_id": "synthetic-session", "tool_name": "Read",
                   "tool_input": {"file_path": "C:/private/report.md"}, "tool_response": {"content": content}}
        stdout, stderr = io.StringIO(), io.StringIO()
        code = run(io.StringIO(json.dumps(payload)), stdout, stderr, self.journal,
                   self.vaults, RecordingNameService())
        self.assertEqual((code, stderr.getvalue()), (0, ""))
        return json.loads(stdout.getvalue()) if stdout.getvalue() else {}

    def assert_protected(self, reply):
        self.assertNotIn("alice@example.com", json.dumps(reply))
        self.assertIn("⟦EMAIL:", reply["hookSpecificOutput"]["updatedToolOutput"]["content"])

    def test_count_only_metadata_is_published_after_real_protection(self):
        self.assert_protected(self.call())
        self.launch.assert_called_once_with(self.directory)
        batch = NotificationQueue(self.directory).take_due(time.time() + 3)[0]
        self.assertEqual(batch["counts"]["pseudonymized"], {"email": 1})
        self.assertEqual(batch["documents"], ["report.md"])
        for secret in ("alice@example.com", "private", "synthetic-session", "⟦"):
            self.assertNotIn(secret, json.dumps(batch))

    def test_queue_failure_keeps_protected_result(self):
        with patch.object(NotificationQueue, "publish", side_effect=OSError("alice@example.com")):
            self.assert_protected(self.call())
        self.launch.assert_not_called()
        log = (self.directory / "delivery.jsonl").read_text()
        self.assertIn("queue_failed", log)
        self.assertNotIn("alice@example.com", log)

    def test_launch_failure_and_unknown_origin_keep_protected_result(self):
        self.capture.side_effect = OSError("alice@example.com")
        self.launch.side_effect = OSError("alice@example.com")
        self.assert_protected(self.call())
        log = (self.directory / "delivery.jsonl").read_text()
        self.assertIn("origin_failed", log)
        self.assertIn("worker_failed", log)
        self.assertNotIn("alice@example.com", log)

    def test_off_and_clean_results_do_no_origin_scan_or_launch(self):
        self.call("Total: 1950 EUR")
        configure(self.directory, "off")
        self.assert_protected(self.call())
        self.capture.assert_not_called()
        self.launch.assert_not_called()

    def test_session_start_does_not_emit_a_protection_notification(self):
        self.call(event="SessionStart")
        self.capture.assert_not_called()
        self.launch.assert_not_called()


class NotificationDeliveryTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.origin = dict(hwnd=123, pid=30, created=99, host="vscode")
        self.batch = {"origin": self.origin, "events": 2, "documents": ["report.md"],
                      "counts": {"pseudonymized": {"email": 4}, "redacted": {"secret": 2}}}
        self.desktop = Mock()
        self.desktop.foreground.return_value = 123
        self.desktop.owner.return_value = (30, 99)
        self.banner = Mock()

    def test_foreground_window_prevents_banner(self):
        self.assertEqual(deliver(self.batch, "background", self.desktop, self.banner, self.directory),
                         "suppress_foreground")
        self.banner.show.assert_not_called()

    def test_focus_is_checked_at_delivery_and_recycled_pid_is_unknown(self):
        self.desktop.foreground.return_value = 456
        self.assertEqual(deliver(self.batch, "background", self.desktop, self.banner, self.directory), "accepted")
        self.assertIn("4 adresses e-mail pseudonymisées", self.banner.show.call_args.args[0])
        self.assertIn("2 secrets masqués", self.banner.show.call_args.args[0])
        self.desktop.owner.return_value = (30, 100)
        self.assertEqual(deliver(self.batch, "background", self.desktop, self.banner, self.directory), "accepted")
        self.assertIn("send_unknown", (self.directory / "delivery.jsonl").read_text())

    def test_native_error_is_best_effort_and_content_free(self):
        self.banner.show.side_effect = OSError("alice@example.com")
        self.assertEqual(deliver(self.batch, "always", self.desktop, self.banner, self.directory), "transport_failed")
        self.assertNotIn("alice@example.com", (self.directory / "delivery.jsonl").read_text())

    def test_disabled_and_missing_preferences_never_enable_silently(self):
        self.assertEqual(read_mode(self.directory), "off")
        journal = Mock()
        self.assertIs(desktop_journal(journal, self.directory), journal)
        (self.directory / "settings.json").write_text('{"version": 1, "mode": ["background"]}')
        self.assertEqual(read_mode(self.directory), "off")

    def test_desktop_body_preserves_categories_and_basename_only(self):
        self.assertEqual(banner_text(self.batch),
                         "report.md\n4 adresses e-mail pseudonymisées.\n2 secrets masqués.\n2 traitements regroupés.")

    def test_large_summary_fits_native_limit_without_cutting_a_word(self):
        self.batch["documents"] = ["x" * 120]
        self.batch["counts"]["pseudonymized"] = {
            kind: 999999 for kind in ("person_name", "email", "phone", "address", "banking", "birth_date", "identifier")}
        text = banner_text(self.batch)
        self.assertLessEqual(len(text.encode("utf-16-le")), 510)
        self.assertIn("6999993 occurrences pseudonymisées", text)
        self.assertTrue(text.endswith("Détails dans Claude Code."))
