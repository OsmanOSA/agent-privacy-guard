"""Custom appearance does not change foreground policy or notification safety."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from privacy_guard.notifications.config import configure, read_mode, read_style
from privacy_guard.notifications.presentation import banner_text, card_content, example_batch
from privacy_guard.notifications.windows_card import WindowsCard


class NotificationCardTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.context = Mock()
        self.context.decision.return_value = "card"

    def test_user_card_preference_does_not_enable_notifications(self):
        configure(self.directory, "off", "card")
        self.assertEqual((read_mode(self.directory), read_style(self.directory)), ("off", "card"))
        configure(self.directory, "background")
        self.assertEqual(read_style(self.directory), "card")
        configure(self.directory, "background", "native")
        self.assertEqual(read_style(self.directory), "native")

    def test_document_and_counts_are_distinct_and_only_basename_is_used(self):
        batch = example_batch()
        batch["documents"] = ["C:/private-folder/report.md"]
        content = card_content(batch)
        self.assertEqual(content["document"], "report.md")
        self.assertEqual(content["headline"], "Pseudonymisation appliquée")
        self.assertEqual(content["details"], "3 noms et 4 adresses e-mail pseudonymisés.")
        self.assertNotIn("private-folder", json.dumps(content))
        self.assertNotIn("C:", banner_text(batch))

    def test_masking_is_not_announced_as_reversible_pseudonymization(self):
        batch = example_batch()
        batch["counts"] = {"pseudonymized": {}, "redacted": {"secret": 2}}
        content = card_content(batch)
        self.assertEqual(content["headline"], "Masquage appliqué")
        self.assertEqual(content["details"], "2 secrets masqués.")

    def test_card_confirmation_does_not_construct_native_fallback(self):
        process = Mock()
        process.start.return_value = "rendered"
        process.pump.return_value = []
        with patch("privacy_guard.notifications.windows_card.CardProcess", return_value=process), \
             patch("privacy_guard.notifications.windows_banner.WindowsBanner") as native:
            card = WindowsCard(self.directory)
            card.show(banner_text(example_batch()), details=card_content(example_batch()), context=self.context)
            self.assertEqual(card.pump(), ["card_rendered"])
            self.assertEqual(card.pump(), [])
            native.assert_not_called()
            card.close()
        process.stop.assert_called_once()

    def test_missing_card_confirmation_keeps_native_delivery(self):
        process, fallback = Mock(), Mock()
        process.start.return_value = "failed"
        fallback.pump.return_value = []
        with patch("privacy_guard.notifications.windows_card.CardProcess", return_value=process), \
             patch("privacy_guard.notifications.windows_banner.WindowsBanner", return_value=fallback):
            card = WindowsCard(self.directory)
            card.show("safe summary", details=card_content(example_batch()), context=self.context)
            fallback.show.assert_called_once_with("safe summary", context=self.context)
            self.assertEqual(card.last_renderer, "native")
            self.assertIn("native_fallback", (self.directory / "delivery.jsonl").read_text())
            card.close()
            fallback.close.assert_called_once()

    def test_render_exception_is_not_echoed_into_delivery_diagnostics(self):
        process, fallback = Mock(), Mock()
        process.start.side_effect = OSError("synthetic-private-body")
        with patch("privacy_guard.notifications.windows_card.CardProcess", return_value=process), \
             patch("privacy_guard.notifications.windows_banner.WindowsBanner", return_value=fallback):
            card = WindowsCard(self.directory)
            card.show("safe summary", details=card_content(example_batch()), context=self.context)
            card.close()
        self.assertNotIn("synthetic-private-body", (self.directory / "delivery.jsonl").read_text())

    def test_long_multilingual_basename_stays_inside_native_fallback_limit(self):
        batch = example_batch()
        batch["documents"] = ["🛡" * 120]
        batch["counts"]["pseudonymized"] = {kind: 999999 for kind in (
            "person_name", "email", "phone", "address", "banking", "birth_date", "identifier")}
        self.assertLessEqual(len(banner_text(batch).encode("utf-16-le")), 510)
