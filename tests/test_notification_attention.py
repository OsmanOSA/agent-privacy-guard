"""Presentation policy must survive focus races, quiet mode, and stale origins."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from privacy_guard.notifications.config import configure
from privacy_guard.notifications.display_context import DisplayContext
from privacy_guard.notifications.windows_card import WindowsCard
from privacy_guard.notifications.windows_interaction import WindowsInteraction, corner


class NotificationAttentionTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        configure(self.directory, "background")
        self.origin = dict(hwnd=123, pid=30, created=99, host="vscode")
        self.desktop = Mock()
        self.desktop.foreground.return_value = 456
        self.desktop.owner.return_value = (30, 99)
        self.attention = Mock(return_value="available")
        self.context = DisplayContext(self.directory, self.origin, desktop=self.desktop, attention=self.attention)

    def test_foreground_changes_are_read_again_before_presentation(self):
        self.assertEqual(self.context.decision(), "card")
        self.desktop.foreground.return_value = 123
        self.assertEqual(self.context.decision(), "suppress_foreground")

    def test_quiet_and_unknown_modes_never_authorize_custom_card(self):
        for mode in ("background", "always"):
            configure(self.directory, mode)
            self.attention.return_value = "quiet"
            self.assertEqual(self.context.decision(), "suppress_quiet")
            self.attention.return_value = "unknown"
            self.assertEqual(self.context.decision(), "native")

    def test_disable_during_startup_is_honored(self):
        self.assertEqual(self.context.decision(), "card")
        configure(self.directory, "off")
        self.assertEqual(self.context.decision(), "off")

    def test_suppression_after_hidden_preparation_does_not_fall_back(self):
        process = Mock()
        process.start.return_value = "suppress_foreground"
        with patch("privacy_guard.notifications.windows_card.CardProcess", return_value=process), \
             patch("privacy_guard.notifications.windows_banner.WindowsBanner") as native:
            card = WindowsCard(self.directory)
            self.assertEqual(card.show("summary", context=self.context), "suppress_foreground")
            native.assert_not_called()
            process.stop.assert_called_once()

    def test_unknown_quiet_state_uses_native_without_starting_wpf(self):
        self.attention.return_value = "unknown"
        with patch("privacy_guard.notifications.windows_card.CardProcess") as process, \
             patch("privacy_guard.notifications.windows_banner.WindowsBanner") as native:
            card = WindowsCard(self.directory)
            card.show("summary", context=self.context)
            process.assert_not_called()
            native.return_value.show.assert_called_once_with("summary", context=self.context)
            card.close()

    def test_visible_card_closes_when_quiet_mode_starts(self):
        process = Mock()
        process.start.return_value = "rendered"
        process.pump.return_value = []
        process.process.poll.return_value = None
        with patch("privacy_guard.notifications.windows_card.CardProcess", return_value=process):
            card = WindowsCard(self.directory)
            card.show("summary", context=self.context)
            self.attention.return_value = "quiet"
            self.assertIn("suppress_quiet", card.pump())
            process.stop.assert_called_once()

    def test_recycled_owner_cannot_be_activated(self):
        desktop = object.__new__(WindowsInteraction)
        desktop.owner = Mock(return_value=(30, 100))
        desktop.user = Mock()
        self.assertFalse(desktop.activate(self.origin))
        desktop.user.SetForegroundWindow.assert_not_called()

    def test_click_returns_to_verified_window_without_executing_commands(self):
        desktop = object.__new__(WindowsInteraction)
        desktop.owner = Mock(return_value=(30, 99))
        desktop.user = Mock()
        desktop.user.IsIconic.return_value = True
        desktop.user.SetForegroundWindow.return_value = True
        self.assertTrue(desktop.activate(self.origin))
        desktop.user.ShowWindowAsync.assert_called_once_with(123, 9)
        desktop.user.SetForegroundWindow.assert_called_once_with(123)

    def test_corner_handles_negative_monitors_and_reserved_taskbar(self):
        self.assertEqual(corner((-1920, -200, 0, 840), 412, 250), (-424, 578))
        self.assertEqual(corner((0, 0, 320, 240), 412, 250), (0, 0))
