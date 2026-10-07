"""Accurate occurrence summaries from actual protection, without value logging."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from privacy_guard.claude_code.hook import run
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from privacy_guard.journal import EventJournal
from privacy_guard.protection_summary import ProtectionSummary
from tests.fakes import STRIPE_KEY, RecordingNameService, ReversingCipher

EMAIL = "alice.martin@example.com"


class ProtectionSummaryTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.names = RecordingNameService()
        self.vaults = VaultStore(self.root / "vault", ReversingCipher())
        self.core = PrivacyCore(self.vaults.session("a"), self.names)
        self.journal = EventJournal(self.root / "logs/guard.log")
        self.summary_file = self.root / "logs/protection.jsonl"

    def call(self, response, tool="Read", path="C:/private-folder/document.txt"):
        payload = {"session_id": "a", "hook_event_name": "PostToolUse", "tool_name": tool,
                   "tool_input": {"file_path": path}, "tool_response": response}
        stdout, stderr = io.StringIO(), io.StringIO()
        code = run(io.StringIO(json.dumps(payload)), stdout, stderr,
                   self.journal, self.vaults, self.names)
        self.assertEqual((code, stderr.getvalue()), (0, ""))
        return json.loads(stdout.getvalue()) if stdout.getvalue() else {}

    def records(self):
        return [json.loads(line) for line in self.summary_file.read_text(encoding="utf-8").splitlines()]

    def test_three_names_and_four_emails_are_counted_in_one_detection_pass(self):
        text = ("Nom : Jean Dupont\nNom : Marie Martin\nNom : Alice Bernard\n"
                f"{EMAIL}\nbob.bernard@example.com\ncarol.martin@example.com\n{EMAIL}")
        reply = self.call({"content": text})
        self.assertEqual(self.names.queried, [text])
        self.assertEqual(reply["systemMessage"],
                         "Privacy Guard — document.txt : 3 noms et 4 adresses e-mail pseudonymisés.")
        row = self.records()[0]
        self.assertEqual(row["pseudonymized"], {"person_name": 3, "email": 4})
        self.assertEqual(row["redacted"], {})
        self.assertEqual(row["count_unit"], "occurrences_in_tool_result")
        self.assertEqual(row["document"], "document.txt")
        for value in ["Jean Dupont", "Marie Martin", "Alice Bernard", EMAIL, "private-folder", "⟦"]:
            self.assertNotIn(value, reply["systemMessage"] + self.summary_file.read_text(encoding="utf-8"))

    def test_counts_aggregate_nested_result_values(self):
        reply = self.call({"stdout": EMAIL, "stderr": "", "details": [{"text": EMAIL}]}, tool="Bash")
        self.assertIn("2 adresses e-mail pseudonymisées", reply["systemMessage"])
        self.assertNotIn("document.txt", reply["systemMessage"])
        self.assertEqual(self.records()[0]["pseudonymized"], {"email": 2})
        self.assertIsNone(self.records()[0]["document"])

    def test_redacted_secrets_are_not_reported_as_reversible_personal_data(self):
        reply = self.call({"content": f"{EMAIL}\n{STRIPE_KEY}\n{STRIPE_KEY}"})
        self.assertIn("1 adresse e-mail pseudonymisée", reply["systemMessage"])
        self.assertIn("2 secrets masqués", reply["systemMessage"])
        self.assertEqual(self.records()[0]["redacted"], {"secret": 2})
        self.assertNotIn(STRIPE_KEY, self.summary_file.read_text(encoding="utf-8"))

    def test_existing_placeholders_are_not_counted_as_new_detections(self):
        first = self.call({"content": EMAIL})
        masked = first["hookSpecificOutput"]["updatedToolOutput"]["content"]
        self.assertNotIn("systemMessage", self.call({"content": masked}))
        self.assertEqual(len(self.records()), 1)
        self.assertEqual(self.core.protect_with_counts(masked), (masked, {}))

    def test_clean_output_creates_no_summary_file(self):
        self.assertEqual(self.call({"content": "Total: 1950 EUR"}), {})
        self.assertFalse(self.summary_file.exists())

    def test_two_reads_append_separate_occurrence_records(self):
        self.call({"content": EMAIL})
        self.call({"content": EMAIL})
        self.assertEqual(len(self.records()), 2)
        self.assertEqual([r["pseudonymized"] for r in self.records()], [{"email": 1}] * 2)

    def test_unknown_detector_category_does_not_enter_ui_or_log(self):
        summary = ProtectionSummary({"untrusted-" + EMAIL: 2})
        self.assertEqual(summary.record()["redacted"], {"other": 2})
        self.assertNotIn(EMAIL, summary.message() + json.dumps(summary.record()))

    def test_related_address_categories_share_one_readable_count(self):
        summary = ProtectionSummary({"postal_address": 1, "fr_postal_address": 2}, "report.md")
        self.assertEqual(summary.message(), "Privacy Guard — report.md : 3 adresses postales pseudonymisées.")

    def test_filename_is_bounded_and_cannot_inject_log_lines_or_bidi_controls(self):
        summary = ProtectionSummary({"email": 1}, "C:\\private\\" + "x" * 140 + "\n\u202e.txt")
        name = summary.record()["document"]
        self.assertEqual(len(name), 120)
        self.assertNotIn("\n", name)
        self.assertNotIn("\u202e", name)
        self.assertNotIn("private", name)
        self.assertTrue(name.endswith("…"))

    def test_invalid_counts_are_rejected(self):
        for count in (True, 0, -1, "1"):
            with self.subTest(count=count), self.assertRaises(ValueError):
                ProtectionSummary({"email": count})

    def test_summary_write_failure_stops_without_releasing_original_values(self):
        with patch.object(self.journal, "record_protection", side_effect=OSError(EMAIL)):
            reply = self.call({"content": EMAIL})
        self.assertFalse(reply["continue"])
        self.assertNotIn(EMAIL, json.dumps(reply))
        self.assertFalse(self.summary_file.exists())
