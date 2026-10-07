"""Real WPF initialization must not display before the final policy decision."""

import sys
import ctypes
from ctypes import wintypes
import unittest
from unittest.mock import Mock

from privacy_guard.notifications.card_process import CardProcess
from privacy_guard.notifications.presentation import card_content, example_batch
from privacy_guard.notifications.windows_interaction import WindowsInteraction


@unittest.skipUnless(sys.platform == "win32", "Windows WPF presentation boundary")
class NotificationHandshakeTest(unittest.TestCase):
    def test_host_focus_change_after_wpf_startup_prevents_any_visible_window(self):
        desktop, context, child = WindowsInteraction(), Mock(), CardProcess()
        self.addCleanup(child.stop)
        observed = []

        def position(hwnd):
            observed.append(bool(desktop.user.IsWindowVisible(hwnd)))
            rect = wintypes.RECT()
            self.assertTrue(desktop.user.GetWindowRect(hwnd, ctypes.byref(rect)))
            self.assertGreaterEqual(rect.bottom - rect.top, 150)
            desktop.place(hwnd, None)

        context.place.side_effect = position
        context.decision.side_effect = ["card", "suppress_foreground"]
        self.assertEqual(child.start(card_content(example_batch()), context), "suppress_foreground")
        self.assertEqual(observed, [False])
        self.assertEqual(child.pump(), [])

    def test_quiet_state_after_wpf_startup_suppresses_without_render_ack(self):
        child, context = CardProcess(), Mock()
        self.addCleanup(child.stop)
        context.decision.return_value = "suppress_quiet"
        self.assertEqual(child.start(card_content(example_batch()), context), "suppress_quiet")
        context.place.assert_not_called()
        self.assertEqual(child.pump(), [])
