"""Regressions from live feedback, using only synthetic names and code."""

import json
import tempfile
import unittest
from pathlib import Path

from privacy_guard.claude_code.protection import protect_tool_output
from privacy_guard.core.findings import Finding
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.personal_data_detector import find_personal_data
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.secret_detector import find_secrets
from privacy_guard.core.vault import VaultStore
from tests.fakes import ReversingCipher


class FragmentDetector:
    def __init__(self, fragment):
        self.fragment, self.calls = fragment, 0

    def find_names(self, text):
        self.calls += 1
        start = text.index(self.fragment)
        return [Finding("person_name", start, start + len(self.fragment))]


class DetectionConsistencyTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.vaults = VaultStore(Path(temporary.name), ReversingCipher())

    def core(self, names=None, session="a"):
        return PrivacyCore(self.vaults.session(session), names or HeuristicNameDetector())

    def test_known_name_is_masked_in_lowercase_list_and_restores_exactly(self):
        text = "Nom : Alice\nusers = ['alice', 'ALICE']"
        core = self.core()
        protected, counts = core.protect_with_counts(text)
        self.assertNotIn("alice", protected.lower())
        self.assertEqual(counts, {"person_name": 3})
        self.assertEqual(core.restore(protected), text)

    def test_detection_in_later_json_value_protects_earlier_value(self):
        output = {"earlier": ["alice"], "later": "Nom : Alice"}
        core = self.core()
        result = protect_tool_output({"tool_name": "Bash", "tool_response": output}, core)
        protected = json.loads(result.stdout)["hookSpecificOutput"]["updatedToolOutput"]
        self.assertNotIn("alice", json.dumps(protected).lower())
        self.assertEqual(core.restore(protected["earlier"][0]), "alice")

    def test_completes_word_after_apostrophe_without_masking_prefix(self):
        text = "Les notes d'Alicia sont prêtes."
        detector = FragmentDetector("Alic")
        core = self.core(detector)
        protected = core.protect(text)
        self.assertIn("d'⟦PERSON_NAME:", protected)
        self.assertNotIn("ia", protected)
        self.assertEqual(core.restore(protected), text)
        self.assertEqual(detector.calls, 1)

    def test_fragment_inside_word_does_not_leave_a_prefix(self):
        text = "Le nom : Mélanie."
        core = self.core(FragmentDetector("lanie"))
        protected = core.protect(text)
        self.assertNotIn("Mé", protected)
        self.assertEqual(core.restore(protected), text)

    def test_hyphenated_and_apostrophized_names_are_complete(self):
        for text, fragment in [("Anne-Marie arrive.", "Marie"), ("O'Connor arrive.", "Connor")]:
            with self.subTest(text=text):
                core = self.core(FragmentDetector(fragment))
                protected = core.protect(text)
                self.assertTrue(protected.startswith("⟦PERSON_NAME:"))
                self.assertEqual(core.restore(protected), text)

    def test_known_name_does_not_match_inside_unrelated_word_or_identifier(self):
        text = "Nom : Alice\nMalice, alice_helper, alice2."
        core = self.core()
        protected = core.protect(text)
        self.assertIn("Malice, alice_helper, alice2", protected)
        self.assertEqual(core.restore(protected), text)

    def test_existing_tokens_survive_name_propagation(self):
        text = "Nom : Alice\nalice\n⟦PERSON_NAME:ABCDEF12⟧"
        core = self.core()
        protected = core.protect(text)
        self.assertIn("⟦PERSON_NAME:ABCDEF12⟧", protected)
        self.assertEqual(core.restore(protected), text)

    def test_new_session_issues_its_own_tokens_and_preserves_historical_ones(self):
        first = self.core().protect("Nom : Alice")
        second_core = self.core(session="b")
        second = second_core.protect("Nom : Alice")
        self.assertNotEqual(first, second)
        self.assertEqual(second_core.protect(first), first)
        self.assertEqual(second_core.restore(first), first)

    def test_diff_decorators_are_not_email_addresses(self):
        for text in ['@app.post("/users")', '+@app.post("/users")', '-@app.post("/users")']:
            with self.subTest(text=text):
                self.assertEqual(find_personal_data(text), [])

    def test_real_email_is_detected_in_diff_and_unusual_local_parts(self):
        for email in ["alice@example.org", "+@example.org", "-@example.org"]:
            text = "+" + email
            self.assertTrue(any(f.kind == "email" for f in find_personal_data(text)), email)

    def test_metric_self_assignment_is_not_a_secret(self):
        for text in ["tokens_estimated=tokens_estimated", "tokenizer_vocab_size=tokenizer_vocab_size"]:
            self.assertEqual(find_secrets(text), [], text)

    def test_literal_secrets_remain_detected(self):
        for text in ['access_token="demo-token-2026-abc"', 'api_key="example1234value"']:
            self.assertTrue(find_secrets(text), text)

    def test_known_name_does_not_swallow_email_or_secret_detection(self):
        text = 'Nom : Alice\nalice@example.org\npassword="Alice-password-2026"'
        core = self.core()
        protected, counts = core.protect_with_counts(text)
        self.assertEqual(counts, {"person_name": 1, "email": 1, "secret_assignment": 1})
        restored = core.restore(protected)
        self.assertIn("alice@example.org", restored)
        self.assertNotIn("Alice-password-2026", restored)

    def test_combining_mark_is_not_left_outside_the_mask(self):
        text = "Jose\u0301 arrive."
        core = self.core(FragmentDetector("Jose"))
        protected = core.protect(text)
        self.assertNotIn("\u0301", protected)
        self.assertEqual(core.restore(protected), text)

    def test_every_string_is_inspected_once_before_propagation(self):
        from tests.fakes import RecordingNameService

        names = RecordingNameService()
        core = self.core(names)
        texts = ["Nom : Alice", "Alice a terminé."]
        protected = core.protect_many_with_counts(texts)
        self.assertEqual(names.queried, texts)
        self.assertEqual([core.restore(text) for text, _ in protected], texts)

    def test_long_identifier_is_unchanged_by_known_name_propagation(self):
        identifier = "Alice" * 2000
        core = self.core()
        protected = core.protect_many_with_counts(["Nom : Alice", identifier])[1]
        self.assertEqual(protected, (identifier, {}))


if __name__ == "__main__":
    unittest.main()
