import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from privacy_guard.core.cipher import default_cipher
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from privacy_guard.exports.command import export_csv

EMAIL = "jean.dupont@example.com"


@unittest.skipUnless(sys.platform == "win32", "Native Windows export")
class ExportCommandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve()
        self.root = self.home / "exports"
        self.root.mkdir()
        self.guard = self.home / "guard"
        self.guard.mkdir()
        (self.guard / "export-policy.json").write_text(
            json.dumps({"version": 1, "root": str(self.root)}), encoding="utf-8"
        )
        vault = VaultStore(self.guard / "vault", default_cipher()).session("a")
        self.token = PrivacyCore(vault, HeuristicNameDetector()).protect(EMAIL)
        self.source = self.home / "masked.csv"
        self.source.write_text(f"email\n{self.token}\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def command(self, filename="clients.csv", session="a"):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = export_csv(self.source, session, filename, self.guard)
        self.assertNotIn(EMAIL, stdout.getvalue() + stderr.getvalue())
        return code, stdout.getvalue(), stderr.getvalue()

    def test_success_receipt_contains_no_originals(self):
        self.assertEqual(self.command(), (0, "CSV export completed.\n", ""))
        self.assertIn(EMAIL, (self.root / "clients.csv").read_text(encoding="utf-8"))
        self.assertEqual(self.source.read_text(encoding="utf-8"), f"email\n{self.token}\n")

    def test_cli_uses_the_explicit_session_and_guard_home(self):
        result = subprocess.run(
            [sys.executable, "-m", "privacy_guard", "export", "--source", str(self.source),
             "--session", "a", "--filename", "clients.csv", "--guard-home", str(self.guard)],
            capture_output=True, text=True, encoding="utf-8"
        )
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "CSV export completed.\n", ""))
        self.assertIn(EMAIL, (self.root / "clients.csv").read_text(encoding="utf-8"))

    def test_missing_policy_fails_without_creating_an_output(self):
        (self.guard / "export-policy.json").unlink()
        self.assertEqual(self.command()[0], 1)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_foreign_session_keeps_tokens_and_never_prints_values(self):
        self.assertEqual(self.command(session="b")[0], 0)
        output = (self.root / "clients.csv").read_text(encoding="utf-8")
        self.assertIn(self.token, output)
        self.assertNotIn(EMAIL, output)

    def test_corrupted_vault_fails_without_an_output(self):
        for path in (self.guard / "vault" / "a").iterdir():
            if path.name != "session.key":
                path.write_bytes(b"corrupt")
        self.assertEqual(self.command()[0], 1)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_filename_and_existing_output_fail(self):
        self.assertEqual(self.command(filename="../outside.csv")[0], 1)
        output = self.root / "clients.csv"
        output.write_text("existing", encoding="utf-8")
        self.assertEqual(self.command()[0], 1)
        self.assertEqual(output.read_text(encoding="utf-8"), "existing")
