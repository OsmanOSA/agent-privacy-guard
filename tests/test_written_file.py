"""Native restoration in the destination selected by the ordinary Write tool."""

import codecs
import csv
import io
import sys
import unittest
from unittest.mock import Mock, patch

from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.exports.written_file import WrittenFileRestorer
from privacy_guard.exports.written_file_handles import WrittenFileHandles
from tests.fakes import STRIPE_KEY
from tests.written_file_fixtures import EMAIL, NAME, ORIGINAL, WrittenFileTestCase


@unittest.skipUnless(sys.platform == "win32", "Native Windows restoration")
class WrittenFileTest(WrittenFileTestCase):
    def test_restores_existing_text_without_returning_content(self):
        path, args = self.written()
        self.assertIs(self.restorer.restore(args, self.core.restore), True)
        self.assertEqual(path.read_text(encoding="utf-8"), ORIGINAL)

    def test_different_directories_and_unicode_filenames_need_no_export_policy(self):
        for name in ("first/results.md", "second/Résultat.txt"):
            with self.subTest(name=name):
                path, args = self.written(name=name)
                self.assertTrue(self.restorer.restore(args, self.core.restore))
                self.assertEqual(path.read_text(encoding="utf-8"), ORIGINAL)
        self.assertFalse((self.home / "export-policy.json").exists())

    def test_source_code_and_configuration_files_get_their_values_back(self):
        token = self.core.protect(EMAIL)
        for name in ("fixtures/user_service.py", "config/settings.yaml", "seed.sql", "app/.env.local"):
            with self.subTest(name=name):
                path, args = self.written(f'CONTACT = "{token}"\n', name)
                self.assertTrue(self.restorer.restore(args, self.core.restore))
                self.assertEqual(path.read_text(encoding="utf-8"), f'CONTACT = "{EMAIL}"\n')

    def test_csv_quotes_restored_values_and_keeps_header_tokens(self):
        token = self.core.protect(EMAIL)
        content = f"{token}\n{token}\n"
        path, args = self.written(content, "result.csv")
        self.assertTrue(self.restorer.restore(args, lambda value: 'Élise, "Morel"\nSecond line'))
        rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8"))))
        self.assertEqual(rows, [[token], ['Élise, "Morel"\nSecond line']])

    def test_preserves_utf8_bom_and_existing_crlf_text(self):
        path, args = self.written()
        path.write_bytes(codecs.BOM_UTF8 + self.masked.replace("\n", "\r\n").encode("utf-8"))
        self.assertTrue(self.restorer.restore(args, self.core.restore))
        self.assertEqual(path.read_bytes(), codecs.BOM_UTF8 + ORIGINAL.replace("\n", "\r\n").encode("utf-8"))

    def test_longer_and_shorter_replacements_truncate_correctly(self):
        for index, replacement in enumerate(("x", "A long value " * 100)):
            path, args = self.written(name=f"result-{index}.txt")
            self.assertTrue(self.restorer.restore(args, lambda _: replacement))
            self.assertEqual(path.read_bytes(), replacement.encode("utf-8"))

    def test_unknown_tokens_leave_bytes_unchanged(self):
        path, args = self.written()
        other = PrivacyCore(self.vaults.session("b"), HeuristicNameDetector())
        before = path.read_bytes()
        self.assertFalse(self.restorer.restore(args, other.restore))
        self.assertEqual(path.read_bytes(), before)

    def test_secrets_stay_redacted_in_a_mixed_output(self):
        protected = self.core.protect(f"Email: {EMAIL}\nSTRIPE_SECRET_KEY={STRIPE_KEY}\n")
        path, args = self.written(protected)
        self.assertTrue(self.restorer.restore(args, self.core.restore))
        output = path.read_text(encoding="utf-8")
        self.assertIn(EMAIL, output)
        self.assertNotIn(STRIPE_KEY, output)
        self.assertIn("⟦STRIPE_SECRET_KEY:REDACTED⟧", output)

    def test_unsupported_paths_formats_and_nul_content_never_lookup(self):
        path, args = self.written()
        restore = Mock()
        for filename in ("relative.txt", r"\\server\share\result.txt", r"\\?\C:\result.txt",
                         str(path) + ":stream", str(self.home / "../result.txt"),
                         str(self.home / "result.xlsx"), str(self.home / "result.txt ")):
            with self.subTest(filename=filename):
                self.assertFalse(self.restorer.restore({**args, "file_path": filename}, restore))
        self.assertFalse(self.restorer.restore({**args, "content": self.masked + "\x00"}, restore))
        restore.assert_not_called()

    def test_mapped_drive_and_reparse_parent_never_lookup(self):
        path, args = self.written()
        restore = Mock()
        with patch("privacy_guard.exports.policy._fixed_local_drive", return_value=False):
            self.assertFalse(self.restorer.restore(args, restore))
        with patch("privacy_guard.exports.written_file._validated_root", return_value=None):
            self.assertFalse(self.restorer.restore(args, restore))
        restore.assert_not_called()

    def test_clean_and_redacted_only_outputs_do_not_open_a_handle(self):
        files = Mock(spec=WrittenFileHandles)
        restorer = WrittenFileRestorer(files)
        for content in ("Amount: 1200 EUR", self.core.protect(STRIPE_KEY)):
            path, args = self.written(content)
            self.assertFalse(restorer.restore(args, self.core.restore))
        files.directory.assert_not_called()
