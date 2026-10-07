"""External placeholders stay readable without exempting surrounding private data."""

import re
import tempfile
import unittest
from pathlib import Path

from privacy_guard.core.bound_values import BoundValues
from privacy_guard.core.findings import Finding
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.tokens import format_token, token_id
from privacy_guard.core.vault import VaultStore
from tests.fakes import ReversingCipher


class MarkerNames:
    def find_names(self, text):
        return [Finding('person_name', m.start(), m.end()) for m in re.finditer(r'PERSON', text)]


class ExternalMarkersTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.vault = VaultStore(Path(temporary.name), ReversingCipher()).session('synthetic')

    def test_all_numbered_markers_stay_literal_even_with_partial_name_predictions(self):
        core = PrivacyCore(self.vault, MarkerNames())
        text = 'M. PERSON_001, [PERSON_002], [PERSON_009], [EMAIL_001].'
        self.assertEqual(core.protect_with_counts(text), (text, {}))

    def test_old_false_positive_mapping_is_not_reused_but_stays_restorable(self):
        marker = 'PERSON_001'
        identifier = token_id(self.vault.session_key(), marker)
        BoundValues(self.vault).store('person_name', identifier, marker)
        core = PrivacyCore(self.vault, HeuristicNameDetector())
        text = '[PERSON_001] puis PERSON_001, [PERSON_009].'
        self.assertEqual(core.protect_with_counts(text), (text, {}))
        self.assertEqual(core.restore(format_token('person_name', identifier)), marker)

    def test_marker_inside_real_mailbox_is_not_an_exemption(self):
        text = 'PERSON_001@example.org et [EMAIL_001]'
        core = PrivacyCore(self.vault, MarkerNames())
        protected, counts = core.protect_with_counts(text)
        self.assertEqual(counts, {'email': 1})
        self.assertNotIn('@example.org', protected)
        self.assertIn('[EMAIL_001]', protected)
        self.assertEqual(core.restore(protected), text)

    def test_real_names_and_emails_next_to_markers_stay_protected(self):
        core = PrivacyCore(self.vault, HeuristicNameDetector())
        text = 'Nom : Alice Martin\n[PERSON_001] = alice@example.org'
        protected, counts = core.protect_with_counts(text)
        self.assertEqual(counts, {'person_name': 1, 'email': 1})
        self.assertIn('[PERSON_001]', protected)
        self.assertEqual(core.restore(protected), text)

    def test_foreign_marker_does_not_disable_secret_detection(self):
        core = PrivacyCore(self.vault, MarkerNames())
        protected, counts = core.protect_with_counts('api_key="PERSON_001"')
        self.assertEqual(counts, {'secret_assignment': 1})
        self.assertIn('REDACTED', protected)

    def test_large_name_prediction_preserves_adjacent_real_name(self):
        class BroadNames:
            def find_names(self, text):
                return [Finding('person_name', 0, len(text))]
        core = PrivacyCore(self.vault, BroadNames())
        text = '[PERSON_001] Alice Martin'
        protected, counts = core.protect_with_counts(text)
        self.assertTrue(protected.startswith('[PERSON_001] '))
        self.assertNotIn('Alice Martin', protected)
        self.assertEqual(counts, {'person_name': 1})
        self.assertEqual(core.restore(protected), text)
