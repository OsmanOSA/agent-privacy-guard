"""Category-bound restoration, legacy isolation, and encrypted record validation."""

import json
import tempfile
import unittest
from pathlib import Path

from privacy_guard.core.bound_values import BoundValues
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.tokens import format_token, token_id
from privacy_guard.core.vault import VaultError, VaultStore
from tests.fakes import ReversingCipher, STRIPE_KEY
from tests.vault_storage import encrypted_record, move_record

EMAIL = "alice.martin@example.com"
IDENTIFIER = "ABCD1234"


class BoundValuesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.vaults = VaultStore(self.root, ReversingCipher())
        self.vault = self.vaults.session("a")
        self.values = BoundValues(self.vault)
        self.core = PrivacyCore(self.vault, HeuristicNameDetector())

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_core_instance_restores_category_bound_values(self):
        token = self.core.protect(EMAIL)
        reopened = PrivacyCore(self.vaults.session("a"), HeuristicNameDetector())
        self.assertEqual(reopened.restore(token), EMAIL)
        self.assertEqual(reopened.protect(EMAIL), token)

    def test_relabeling_a_personal_token_keeps_it_masked(self):
        token = self.core.protect(EMAIL).replace("EMAIL:", "PERSON_NAME:")
        self.assertEqual(self.core.restore(token), token)

    def test_legacy_secret_cannot_restore_through_a_personal_label(self):
        identifier = token_id(self.vault.session_key(), STRIPE_KEY)
        self.vault.store(identifier, STRIPE_KEY)
        before = {path.name: path.read_bytes() for path in (self.root / "a").iterdir()}
        forged = format_token("email", identifier)
        self.assertEqual(self.core.restore(forged), forged)
        after = {path.name: path.read_bytes() for path in (self.root / "a").iterdir()}
        self.assertEqual(after, before)

    def test_legacy_personal_mapping_stays_masked_without_migration(self):
        identifier = token_id(self.vault.session_key(), EMAIL)
        self.vault.store(identifier, EMAIL)
        legacy_token = format_token("email", identifier)
        self.assertEqual(self.core.restore(legacy_token), legacy_token)
        fresh_token = self.core.protect(EMAIL)
        self.assertEqual(self.core.restore(fresh_token), EMAIL)
        self.assertEqual(self.vault.lookup(identifier), EMAIL)

    def test_ciphertext_moved_to_another_category_is_rejected(self):
        self.values.store("email", IDENTIFIER, EMAIL)
        directory = self.root / "a"
        move_record(directory, f"bound-email-{IDENTIFIER}", f"bound-person_name-{IDENTIFIER}")
        with self.assertRaises(VaultError):
            self.values.lookup("person_name", IDENTIFIER)

    def test_ciphertext_moved_to_another_identifier_is_rejected(self):
        self.values.store("email", IDENTIFIER, EMAIL)
        directory = self.root / "a"
        move_record(directory, f"bound-email-{IDENTIFIER}", "bound-email-1234ABCD")
        with self.assertRaises(VaultError):
            self.values.lookup("email", "1234ABCD")

    def test_invalid_encrypted_record_fails_without_returning_a_value(self):
        records = ("not json", json.dumps({"version": True, "kind": "email", "identifier": IDENTIFIER, "value": EMAIL}),
                   json.dumps({"version": 1, "kind": "email", "identifier": IDENTIFIER, "value": 123}), "[]")
        for encoded in records:
            with self.subTest(encoded=encoded):
                directory = self.root / "a"
                directory.mkdir(exist_ok=True)
                (directory / f"bound-email-{IDENTIFIER}").write_bytes(ReversingCipher().encrypt(encoded.encode("utf-8")))
                with self.assertRaises(VaultError):
                    self.values.lookup("email", IDENTIFIER)

    def test_secret_unknown_kind_and_unsafe_identifier_cannot_be_stored(self):
        for kind, identifier in (("stripe_secret_key", IDENTIFIER), ("unknown", IDENTIFIER),
                                 ("email", "../escape"), ("email", "abcd1234")):
            with self.subTest(kind=kind, identifier=identifier), self.assertRaises(VaultError):
                self.values.store(kind, identifier, EMAIL)
        self.assertFalse((self.root / "a").exists())

    def test_records_are_encrypted_and_session_specific(self):
        self.values.store("email", IDENTIFIER, EMAIL)
        self.assertIsNone(BoundValues(self.vaults.session("b")).lookup("email", IDENTIFIER))
        encrypted = encrypted_record(self.root / "a", f"bound-email-{IDENTIFIER}")
        self.assertTrue(encrypted.startswith(ReversingCipher.PREFIX))
        self.assertNotIn(EMAIL.encode(), encrypted)

    def test_conflicting_value_does_not_replace_the_original(self):
        self.values.store("email", IDENTIFIER, EMAIL)
        with self.assertRaises(VaultError):
            self.values.store("email", IDENTIFIER, "other@example.com")
        self.assertEqual(self.values.lookup("email", IDENTIFIER), EMAIL)
