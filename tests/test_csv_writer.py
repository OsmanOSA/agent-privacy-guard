import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from privacy_guard.exports.policy import CsvExportPolicy
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from privacy_guard.exports.csv_writer import CsvWriter
from privacy_guard.exports.windows_files import WindowsFiles
from tests.fakes import ReversingCipher, STRIPE_KEY

EMAIL = "jean.dupont@example.com"


@unittest.skipUnless(sys.platform == "win32", "Native Windows writer")
class CsvWriterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve()
        self.root = self.home / "exports"
        self.root.mkdir()
        self.policy = CsvExportPolicy(self.root)
        self.core = PrivacyCore(VaultStore(self.home / "vault", ReversingCipher()).session("a"), HeuristicNameDetector())
        self.token = self.core.protect(EMAIL)
        self.content = f"email\n{self.token}\n"
        self.writer = CsvWriter(self.policy)

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_restored_values_to_a_new_csv(self):
        self.assertIsNone(self.writer.write("clients.csv", self.content, self.core.restore))
        rows = list(csv.reader(io.StringIO((self.root / "clients.csv").read_text(encoding="utf-8"))))
        self.assertEqual(rows, [["email"], [EMAIL]])

    def test_never_overwrites_an_existing_file(self):
        target = self.root / "clients.csv"
        target.write_text("existing", encoding="utf-8")
        restore = Mock()
        with self.assertRaises(ValueError):
            self.writer.write("clients.csv", self.content, restore)
        restore.assert_not_called()
        self.assertEqual(target.read_text(encoding="utf-8"), "existing")

    def test_creation_race_preserves_competing_file(self):
        target = self.root / "clients.csv"

        def competing_restore(value):
            target.write_text("competing", encoding="utf-8")
            return self.core.restore(value)

        with self.assertRaises(OSError):
            self.writer.write("clients.csv", self.content, competing_restore)
        self.assertEqual(target.read_text(encoding="utf-8"), "competing")

    def test_competing_hard_link_cannot_modify_another_file(self):
        outside = self.home / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        target = self.root / "clients.csv"

        def competing_restore(value):
            target.hardlink_to(outside)
            return self.core.restore(value)

        with self.assertRaises(OSError):
            self.writer.write("clients.csv", self.content, competing_restore)
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside")

    def test_utf8_and_quoting_preserve_cell_values_in_the_written_file(self):
        original = 'Élise, "Morel"\nSecond line'
        self.writer.write("clients.csv", self.content, lambda _: original)
        rows = list(csv.reader(io.StringIO((self.root / "clients.csv").read_text(encoding="utf-8"))))
        self.assertEqual(rows, [["email"], [original]])

    def test_file_is_not_readable_before_the_exclusive_handle_closes(self):
        target = self.root / "clients.csv"
        test = self

        class InspectingFiles(WindowsFiles):
            def write(self, handle, data):
                with test.assertRaises(OSError):
                    target.read_bytes()
                super().write(handle, data)

        CsvWriter(self.policy, InspectingFiles()).write("clients.csv", self.content, self.core.restore)
        self.assertIn(EMAIL, target.read_text(encoding="utf-8"))

    def test_export_directory_and_parent_cannot_move_during_restoration(self):
        def restore(value):
            for directory in (self.root, self.home):
                with self.assertRaises(OSError):
                    directory.rename(directory.with_name(directory.name + "-moved"))
            return self.core.restore(value)

        self.writer.write("clients.csv", self.content, restore)
        self.assertIn(EMAIL, (self.root / "clients.csv").read_text(encoding="utf-8"))

    def test_invalid_content_creates_no_output(self):
        for content in ('email\n"unterminated', "email\n=1+1\n"):
            with self.assertRaises(ValueError):
                self.writer.write("clients.csv", content, self.core.restore)
        self.assertFalse((self.root / "clients.csv").exists())

    def test_filenames_cannot_change_directory_or_open_streams(self):
        for filename in ("../clients.csv", "nested/clients.csv", str(self.root / "clients.csv"), "clients.csv:extra", "CON.csv"):
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                self.writer.write(filename, self.content, self.core.restore)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_handled_write_failure_discards_the_created_file(self):
        class FailingFiles(WindowsFiles):
            def write(self, handle, data):
                super().write(handle, data[:5])
                raise OSError("synthetic failure")

        writer = CsvWriter(self.policy, FailingFiles())
        with self.assertRaises(OSError):
            writer.write("clients.csv", self.content, self.core.restore)
        self.assertFalse((self.root / "clients.csv").exists())

    def test_secrets_stay_redacted_in_the_real_output_file(self):
        marker = self.core.protect(STRIPE_KEY)
        self.writer.write("clients.csv", f"credential\n{marker}\n", self.core.restore)
        output = (self.root / "clients.csv").read_text(encoding="utf-8")
        self.assertIn(marker, output)
        self.assertNotIn(STRIPE_KEY, output)

    def test_restore_error_creates_no_output(self):
        def broken(_):
            raise OSError("synthetic vault error")

        with self.assertRaises(OSError):
            self.writer.write("clients.csv", self.content, broken)
        self.assertFalse((self.root / "clients.csv").exists())
