"""Synthetic native-file fixtures for automatic restoration tests."""

import tempfile
import unittest
from pathlib import Path

from privacy_guard.core.cipher import default_cipher
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from privacy_guard.exports.written_file import WrittenFileRestorer

EMAIL = "alice.martin@example.com"
NAME = "Alice Martin"
ORIGINAL = f"Name: {NAME}\nEmail: {EMAIL}\nAmount: 1200 EUR\n"


class WrittenFileTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve()
        self.vaults = VaultStore(self.home / "vault", default_cipher())
        self.core = PrivacyCore(self.vaults.session("a"), HeuristicNameDetector())
        self.masked = self.core.protect(ORIGINAL)
        self.restorer = WrittenFileRestorer()

    def tearDown(self):
        self.tmp.cleanup()

    def written(self, content=None, name="result.txt"):
        content = self.masked if content is None else content
        path = self.home / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")
        return path, {"file_path": str(path), "content": content}
