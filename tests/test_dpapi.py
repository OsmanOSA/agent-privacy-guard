import sys
import tempfile
import unittest
from pathlib import Path

from privacy_guard.core.vault import VaultStore
from tests.fakes import STRIPE_KEY as SECRET


@unittest.skipUnless(sys.platform == "win32", "DPAPI exists on Windows only")
class DpapiCipherTest(unittest.TestCase):
    def setUp(self):
        from privacy_guard.core.dpapi import DpapiCipher

        self.cipher = DpapiCipher()

    def test_round_trip(self):
        self.assertEqual(self.cipher.decrypt(self.cipher.encrypt(b"value")), b"value")

    def test_ciphertext_does_not_contain_the_plaintext(self):
        self.assertNotIn(SECRET.encode(), self.cipher.encrypt(SECRET.encode()))

    def test_rejects_tampered_data(self):
        encrypted = self.cipher.encrypt(b"value")

        with self.assertRaises(OSError):
            self.cipher.decrypt(encrypted[:-4] + b"\x00\x00\x00\x00")

    def test_no_secret_in_clear_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = VaultStore(Path(tmp), self.cipher).session("session-a")
            vault.store("ABCD1234", SECRET)

            stored = (Path(tmp) / "session-a" / "ABCD1234").read_bytes()

            self.assertNotIn(SECRET.encode(), stored)
            self.assertEqual(vault.lookup("ABCD1234"), SECRET)


if __name__ == "__main__":
    unittest.main()
