"""Native Windows lifecycle, metadata and callback checks without live banners."""

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

from privacy_guard.claude_code.installer import ClaudeCodeInstaller
from privacy_guard.notifications.config import configure
from privacy_guard.notifications.lifecycle import WorkerLease, ensure_worker, stop_worker
from privacy_guard.notifications.queue import NotificationQueue
from privacy_guard.notifications.worker import deliver


@unittest.skipUnless(sys.platform == "win32", "Native Windows notifications")
class WindowsNotificationsTest(unittest.TestCase):
    def test_native_callback_and_tray_cleanup_without_sending_a_banner(self):
        from ctypes import wintypes as w
        from privacy_guard.notifications.windows_banner import WindowsBanner, CALLBACK
        banner = WindowsBanner()
        try:
            send = banner.user.SendMessageW
            send.argtypes, send.restype = [w.HWND, w.UINT, w.WPARAM, w.LPARAM], ctypes.c_ssize_t
            send(banner.data.hWnd, CALLBACK, 0, 0x402)
            self.assertEqual(banner.pump(), ["displayed"])
            self.assertEqual(banner.pump(), [])
        finally:
            banner.close()
        self.assertIsNone(banner.data.hWnd)

    def test_detached_worker_starts_once_and_stops_without_a_console_window(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            configure(directory, "background")
            try:
                ensure_worker(directory)
                deadline = time.monotonic() + 8
                while not (directory / "worker.live").exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertTrue((directory / "worker.live").exists())
                duplicate = WorkerLease(directory)
                self.assertIsNone(duplicate.handle)
                ensure_worker(directory)
                self.assertFalse((directory / "launch.claim").exists())
            finally:
                stop_worker(directory)
            self.assertFalse((directory / "worker.live").exists())
            lease = WorkerLease(directory)
            self.assertIsNotNone(lease.handle)
            lease.close()

    def test_installed_hook_queues_committed_counts_in_an_isolated_home(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            claude, guard = home / ".claude", home / ".privacy-guard"
            claude.mkdir()
            installer = ClaudeCodeInstaller(claude, guard, Path(sys.executable))
            installer.install()
            directory = guard / "notifications"
            configure(directory, "background")
            # Inhibit desktop delivery in this automated test; replay at boundary.
            (directory / "stop").touch()
            try:
                env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
                payload = dict(hook_event_name="PostToolUse", session_id="synthetic-session", tool_name="Bash",
                               tool_response={"stdout": "alice@example.com", "stderr": ""})
                output = subprocess.run([sys.executable, str(guard / "app")], input=json.dumps(payload),
                                        capture_output=True, text=True, encoding="utf-8", env=env, timeout=15)
                self.assertEqual((output.returncode, output.stderr), (0, ""))
                reply = json.loads(output.stdout)
                self.assertNotIn("alice@example.com", output.stdout)
                self.assertIn("⟦EMAIL:", reply["hookSpecificOutput"]["updatedToolOutput"]["stdout"])
                batch = NotificationQueue(directory).take_due(time.time() + 3)[0]
                self.assertEqual(batch["counts"]["pseudonymized"], {"email": 1})
                self.assertNotIn("alice@example.com", json.dumps(batch))
                desktop, banner = Mock(), Mock()
                self.assertEqual(deliver(batch, "always", desktop, banner, directory), "accepted")
                banner.show.assert_called_once()
            finally:
                configure(directory, "off")
                installer.uninstall()
