"""Recognise committed names after reopening the same encrypted session vault."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

from privacy_guard.core.bound_values import BoundValues
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.tokens import token_id
from privacy_guard.core.vault import VaultError, VaultStore
from tests.fakes import ReversingCipher


class SessionNamesTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.cipher = ReversingCipher()

    def core(self, session='a'):
        return PrivacyCore(VaultStore(self.root, self.cipher).session(session), HeuristicNameDetector())

    def test_reopened_core_masks_lowercase_name_without_a_label(self):
        first = self.core().protect('Nom : Alice')
        text = "users = ['alice', 'ALICE']"
        reopened = self.core()
        protected, counts = reopened.protect_with_counts(text)
        self.assertEqual(counts, {'person_name': 2})
        self.assertNotIn('alice', protected.lower())
        self.assertEqual(reopened.restore(protected), text)
        self.assertEqual(reopened.protect('Nom : Alice'), first)

    def test_other_sessions_do_not_learn_the_name(self):
        self.core().protect('Nom : Alice')
        self.assertEqual(self.core('b').protect('alice'), 'alice')

    def test_full_name_does_not_infer_ambiguous_aliases(self):
        self.core().protect('Nom : Alice Martin')
        core = self.core()
        self.assertNotEqual(core.protect('alice martin'), 'alice martin')
        self.assertEqual(core.protect('alice, martin'), 'alice, martin')

    def test_known_names_preserve_boundaries_and_other_categories(self):
        self.core().protect('Nom : Alice')
        text = 'Malice alice_helper alice2 alice@example.org ⟦PERSON_NAME:ABCDEF12⟧'
        protected = self.core().protect(text)
        self.assertIn('Malice alice_helper alice2', protected)
        self.assertIn('⟦EMAIL:', protected)
        self.assertIn('⟦PERSON_NAME:ABCDEF12⟧', protected)

    def test_legacy_bound_name_file_is_recognised_without_modification(self):
        vault = VaultStore(self.root, self.cipher).session('a')
        identifier = token_id(vault.session_key(), 'Alice')
        record = dict(version=1, kind='person_name', identifier=identifier, value='Alice')
        path = self.root / 'a' / ('bound-person_name-' + identifier)
        path.write_bytes(self.cipher.encrypt(json.dumps(record).encode()))
        original = path.read_bytes()
        core = self.core()
        self.assertNotEqual(core.protect('alice'), 'alice')
        self.assertEqual(path.read_bytes(), original)

    def test_corrupt_name_record_blocks_instead_of_forgetting(self):
        self.core().protect('Nom : Alice')
        path = self.root / 'a' / 'personal.sqlite3'
        with closing(sqlite3.connect(path)) as db:
            db.execute("UPDATE records SET payload=? WHERE key LIKE 'bound-person_name-%'", (b'broken',))
            db.commit()
        with self.assertRaises((VaultError, ValueError)):
            self.core().protect('alice')

    def test_rolled_back_names_are_not_learned(self):
        vault = VaultStore(self.root, self.cipher).session('a')
        with self.assertRaises(RuntimeError):
            with vault.batch():
                BoundValues(vault).store('person_name', 'ABCDEF12', 'Alice')
                raise RuntimeError('Interrupted')
        self.assertEqual(self.core().protect('alice'), 'alice')

    def test_concurrent_committed_names_are_both_available(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda name: self.core().protect('Nom : ' + name), ['Alice', 'Camille']))
        protected, counts = self.core().protect_with_counts('alice et camille')
        self.assertEqual(counts, {'person_name': 2})
        self.assertNotIn('alice', protected)

    def test_clean_session_read_does_not_create_a_database(self):
        self.assertEqual(self.core().protect('ordinary output'), 'ordinary output')
        self.assertFalse(self.root.joinpath('a').exists())


if __name__ == '__main__':
    unittest.main()
