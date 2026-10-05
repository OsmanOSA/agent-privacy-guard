import os
import tempfile
import time
import unittest
from pathlib import Path

from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultError, VaultStore
from tests.fakes import STRIPE_KEY, ReversingCipher

PLAYGROUND_ENV = Path(__file__).resolve().parent.parent / "playground" / ".env"
OTHER_KEY = "sk_live_" + "OTHEROTHEROTHER000000000000"


class PrivacyCoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.vaults = VaultStore(self.root, ReversingCipher())
        self.core = PrivacyCore(self.vaults.session("session-a"), HeuristicNameDetector())

    def tearDown(self):
        self._tmp.cleanup()

    def test_round_trip_restores_the_exact_original(self):
        env = PLAYGROUND_ENV.read_text(encoding="utf-8")

        protected = self.core.protect(env)

        self.assertNotIn(STRIPE_KEY, protected)
        self.assertNotIn("FakePassw0rd123", protected)
        self.assertEqual(self.core.restore(protected), env)

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
        self.assertEqual(self.core.protect(STRIPE_KEY), self.core.protect(STRIPE_KEY))

    def test_different_values_get_different_tokens(self):
        self.assertNotEqual(self.core.protect(STRIPE_KEY), self.core.protect(OTHER_KEY))

    def test_never_tokenizes_a_token(self):
        protected = self.core.protect(f"STRIPE_SECRET_KEY={STRIPE_KEY}")

        self.assertEqual(self.core.protect(protected), protected)

    def test_leaves_unknown_tokens_untouched(self):
        foreign_token = PrivacyCore(self.vaults.session("session-b"), HeuristicNameDetector()).protect(STRIPE_KEY)

        self.assertEqual(self.core.restore(foreign_token), foreign_token)

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
