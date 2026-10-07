"""Notification policy with synthetic windows; no desktop operations in tests."""

import json
import tempfile
import unittest
from pathlib import Path

from privacy_guard.notifications.policy import choose_origin, delivery_policy
from privacy_guard.notifications.queue import NotificationQueue
from privacy_guard.protection_summary import ProtectionSummary


class NotificationPolicyTest(unittest.TestCase):
    def test_nearest_single_host_window_is_selected(self):
        processes = {10: (20, "python.exe"), 20: (30, "bash.exe"), 30: (40, "Code.exe")}
        self.assertEqual(choose_origin(10, processes, {30: [123]}), (30, 123, "vscode"))

    def test_multiple_editor_windows_are_ambiguous(self):
        self.assertIsNone(choose_origin(10, {10: (20, "python.exe"), 20: (0, "Code.exe")}, {20: [1, 2]}))

    def test_no_process_name_only_suppression(self):
        self.assertIsNone(choose_origin(1, {1: (0, "Code.exe")}, {}))
        self.assertEqual(delivery_policy("background", None, 100, None), "send_unknown")

    def test_window_and_owner_lifetime_must_both_match(self):
        origin = {"hwnd": 123, "pid": 30, "created": 99, "host": "vscode"}
        self.assertEqual(delivery_policy("background", origin, 123, (30, 99)), "suppress_foreground")
        self.assertEqual(delivery_policy("background", origin, 456, (30, 99)), "send_background")
        self.assertEqual(delivery_policy("background", origin, 123, (30, 100)), "send_unknown")
        self.assertEqual(delivery_policy("always", origin, 123, (30, 99)), "send_always")
        self.assertEqual(delivery_policy("off", origin, 456, (30, 99)), "off")


class NotificationQueueTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.queue = NotificationQueue(self.root)
        self.summary = ProtectionSummary({"person_name": 3, "email": 4}, "C:/private/report.md")

    def test_grouping_has_a_maximum_wait_even_with_continuous_events(self):
        for now in range(10):
            self.queue.publish("session-a", None, self.summary, now)
        rows = self.queue.take_due(10)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["events"], 10)
        self.assertEqual(row["counts"]["pseudonymized"], {"person_name": 30, "email": 40})
        self.assertEqual(row["documents"], ["report.md"])
        stored = json.dumps(row)
        self.assertNotIn("session-a", stored)
        self.assertNotIn("private", stored)
        self.assertEqual(self.queue.take_due(11), [])

    def test_sessions_and_expiration_are_separate(self):
        self.queue.publish("a", None, self.summary, 0)
        self.queue.publish("b", None, self.summary, 121)
        rows = self.queue.take_due(124)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["events"], 1)

    def test_cooldown_keeps_counts_without_notification_flood(self):
        self.queue.publish("a", None, self.summary, 0)
        self.assertEqual(len(self.queue.take_due(3)), 1)
        self.queue.publish("a", None, self.summary, 4)
        self.assertEqual(self.queue.take_due(7), [])
        self.assertEqual(len(self.queue.take_due(33)), 1)

    def test_pending_session_limit_is_bounded(self):
        for index in range(140):
            self.queue.publish(str(index), None, self.summary, index / 100)
        self.assertEqual(len(self.queue.take_due(12)), 128)

    def test_clock_rollback_does_not_keep_old_messages_forever(self):
        self.queue.publish("a", None, self.summary, 1000)
        self.assertEqual(self.queue.take_due(1), [])
        self.queue.publish("a", None, self.summary, 2)
        self.assertEqual(len(self.queue.take_due(5)), 1)
