import os
import tempfile
import time
import unittest
from pathlib import Path

from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.tokens import format_token, token_id
from privacy_guard.core.vault import VaultError, VaultStore
from tests.fakes import STRIPE_KEY, ReversingCipher

EMAIL = "jean.dupont@example.com"
OTHER_EMAIL = "marie.martin@example.com"


class PrivacyCoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.vaults = VaultStore(self.root, ReversingCipher())
        self.core = PrivacyCore(self.vaults.session("session-a"), HeuristicNameDetector())

    def tearDown(self):
        self._tmp.cleanup()

    def test_round_trip_restores_the_exact_original(self):
        original = f"Nom : Jean Dupont\nEmail={EMAIL}\nTéléphone : +33 6 12 34 56 78"

        protected = self.core.protect(original)

        self.assertNotIn("Jean Dupont", protected)
        self.assertNotIn(EMAIL, protected)
        self.assertEqual(self.core.restore(protected), original)

    def test_protects_personal_data(self):
        protected = self.core.protect("ADMIN_EMAIL=jean.dupont@example.com\nPHONE=+33 6 12 34 56 78")

        self.assertNotIn("jean.dupont", protected)
        self.assertNotIn("12 34 56 78", protected)
        self.assertIn("⟦EMAIL:", protected)
        self.assertIn("⟦PHONE:", protected)

    def test_protects_person_names(self):
        protected = self.core.protect("Nom : Jean Dupont\nBonjour Madame Marie Martin")

        self.assertNotIn("Dupont", protected)
        self.assertNotIn("Marie Martin", protected)
        self.assertEqual(protected.count("⟦PERSON_NAME:"), 2)

    def test_url_password_is_not_swallowed_by_an_email_match(self):
        protected = self.core.protect("postgres://admin:FakePass123@db.example.com:5432/app")

        self.assertIn("⟦URL_PASSWORD:", protected)
        self.assertIn("@db.example.com:5432/app", protected)

    def test_same_value_gets_the_same_token(self):
        self.assertEqual(self.core.protect(EMAIL), self.core.protect(EMAIL))

    def test_different_values_get_different_tokens(self):
        self.assertNotEqual(self.core.protect(EMAIL), self.core.protect(OTHER_EMAIL))

    def test_never_tokenizes_a_token(self):
        protected = self.core.protect(f"STRIPE_SECRET_KEY={STRIPE_KEY}")

        self.assertEqual(self.core.protect(protected), protected)

    def test_leaves_unknown_tokens_untouched(self):
        foreign_token = PrivacyCore(self.vaults.session("session-b"), HeuristicNameDetector()).protect(EMAIL)

        self.assertEqual(self.core.restore(foreign_token), foreign_token)

    def test_secrets_redact_without_creating_a_vault(self):
        original = f"STRIPE_SECRET_KEY={STRIPE_KEY}\npassword=FakePassw0rd123"

        protected = self.core.protect(original)

        self.assertEqual(protected, "STRIPE_SECRET_KEY=⟦STRIPE_SECRET_KEY:REDACTED⟧\npassword=⟦SECRET_ASSIGNMENT:REDACTED⟧")
        self.assertEqual(self.core.restore(protected), protected)
        self.assertFalse((self.root / "session-a").exists())

    def test_mixed_output_restores_personal_values_only(self):
        protected = self.core.protect(f"Email={EMAIL}\nSTRIPE_SECRET_KEY={STRIPE_KEY}")

        self.assertEqual(self.core.restore(protected), f"Email={EMAIL}\nSTRIPE_SECRET_KEY=⟦STRIPE_SECRET_KEY:REDACTED⟧")
        vault = self.vaults.session("session-a")
        self.assertIsNone(vault.lookup(token_id(vault.session_key(), STRIPE_KEY)))

    def test_legacy_secret_kind_tokens_do_not_restore(self):
        vault = self.vaults.session("session-a")
        identifier = token_id(vault.session_key(), STRIPE_KEY)
        vault.store(identifier, STRIPE_KEY)
        token = format_token("stripe_secret_key", identifier)

        self.assertEqual(self.core.restore(token), token)

    def test_relabeling_a_new_redaction_cannot_recover_a_value(self):
        marker = self.core.protect(STRIPE_KEY)
        relabeled = marker.replace("STRIPE_SECRET_KEY", "EMAIL")

        self.assertEqual(self.core.restore(relabeled), relabeled)
        self.assertFalse((self.root / "session-a").exists())

    def test_unknown_token_kind_cannot_access_a_personal_mapping(self):
        token = self.core.protect(EMAIL).replace("EMAIL:", "UNKNOWN:")

        self.assertEqual(self.core.restore(token), token)

    def test_existing_markers_are_not_sent_back_to_the_vault(self):
        marker = "⟦SECRET_ASSIGNMENT:REDACTED⟧"

        self.assertEqual(self.core.protect(f"password={marker}"), f"password={marker}")
        self.assertFalse((self.root / "session-a").exists())

    def test_clean_text_touches_no_disk(self):
        self.core.protect("PORT=3000")
        self.core.restore("nothing to restore")

        self.assertFalse((self.root / "session-a").exists())


class SessionVaultTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.vaults = VaultStore(self.root, ReversingCipher())
        self.vault = self.vaults.session("session-a")

    def tearDown(self):
        self._tmp.cleanup()

    def test_session_key_is_stable(self):
        self.assertEqual(self.vault.session_key(), self.vaults.session("session-a").session_key())

    def test_rejects_a_second_value_for_the_same_token(self):
        self.vault.store("ABCD1234", "first")

        with self.assertRaises(VaultError):
            self.vault.store("ABCD1234", "second")

    def test_rejects_unsafe_session_ids(self):
        with self.assertRaises(VaultError):
            self.vaults.session("../escape")

    def test_close_session_deletes_its_vault_only(self):
        self.vault.store("ABCD1234", "value")
        other = self.vaults.session("session-b")
        other.store("ABCD1234", "value")

        self.vaults.close_session("session-a")

        self.assertFalse((self.root / "session-a").exists())
        self.assertEqual(other.lookup("ABCD1234"), "value")

    def test_close_session_purges_abandoned_vaults(self):
        abandoned = self.vaults.session("crashed-session")
        abandoned.store("ABCD1234", "value")
        self._age(self.root / "crashed-session", days=8)

        self.vaults.close_session("session-a")

        self.assertFalse((self.root / "crashed-session").exists())

    def test_close_session_keeps_recently_active_vaults(self):
        recent = self.vaults.session("open-session")
        recent.store("ABCD1234", "value")
        self._age(self.root / "open-session", days=6)

        self.vaults.close_session("session-a")

        self.assertEqual(recent.lookup("ABCD1234"), "value")

    def _age(self, directory, days):
        past = time.time() - days * 24 * 3600
        for path in [directory, *directory.iterdir()]:
            os.utime(path, (past, past))

    def test_writes_only_encrypted_bytes(self):
        self.vault.store("ABCD1234", STRIPE_KEY)
        self.vault.session_key()

        for path in (self.root / "session-a").iterdir():
            self.assertTrue(path.read_bytes().startswith(ReversingCipher.PREFIX), path.name)
        self.assertEqual(self.vault.lookup("ABCD1234"), STRIPE_KEY)


if __name__ == "__main__":
    unittest.main()
