"""Content races, alias rejection, exclusive access, and masked-byte rollback."""

import sys
import unittest
from unittest.mock import Mock, patch

from privacy_guard.exports.written_file import WrittenFileRestorer
from privacy_guard.exports.written_file_handles import WrittenFileHandles
from tests.written_file_fixtures import EMAIL, WrittenFileTestCase
from tests.vault_storage import corrupt_records


@unittest.skipUnless(sys.platform == "win32", "Native Windows restoration")
class WrittenFileFailureTest(WrittenFileTestCase):
    def test_replaced_content_is_preserved_without_restoring(self):
        path, args = self.written()
        path.write_text("competing content", encoding="utf-8")
        restore = Mock()
        with self.assertRaises(ValueError):
            self.restorer.restore(args, restore)
        restore.assert_not_called()
        self.assertEqual(path.read_text(encoding="utf-8"), "competing content")

    def test_existing_hard_link_preserves_both_names_without_lookup(self):
        path, args = self.written()
        alias = self.home / "alias.txt"
        alias.hardlink_to(path)
        restore = Mock()
        with self.assertRaises(OSError):
            self.restorer.restore(args, restore)
        restore.assert_not_called()
        self.assertEqual(alias.read_text(encoding="utf-8"), self.masked)

    def test_file_and_parent_directories_are_exclusively_held_during_lookup(self):
        path, args = self.written(name="results/report.txt")

        def restore(value):
            with self.assertRaises(OSError):
                path.read_bytes()
            with self.assertRaises(OSError):
                path.write_text("competing", encoding="utf-8")
            for target in (path, path.parent, self.home):
                with self.assertRaises(OSError):
                    target.rename(target.with_name(target.name + "-moved"))
            return self.core.restore(value)

        self.assertTrue(self.restorer.restore(args, restore))
        self.assertIn(EMAIL, path.read_text(encoding="utf-8"))

    def test_alias_created_during_lookup_keeps_both_files_masked(self):
        path, args = self.written()
        alias = self.home / "new-alias.txt"

        def restore(value):
            alias.hardlink_to(path)
            return self.core.restore(value)

        with self.assertRaises(OSError):
            self.restorer.restore(args, restore)
        self.assertEqual(path.read_text(encoding="utf-8"), self.masked)
        self.assertEqual(alias.read_text(encoding="utf-8"), self.masked)

    def test_alias_created_during_replacement_rolls_back_before_close(self):
        path, args = self.written()
        alias = self.home / "late-alias.txt"

        class LinkingOnce(WrittenFileHandles):
            linked = False

            def replace(self, handle, data):
                if not self.linked:
                    self.linked = True
                    alias.hardlink_to(path)
                super().replace(handle, data)

        with self.assertRaises(OSError):
            WrittenFileRestorer(LinkingOnce()).restore(args, self.core.restore)
        self.assertEqual(path.read_text(encoding="utf-8"), self.masked)
        self.assertEqual(alias.read_text(encoding="utf-8"), self.masked)

    def test_handled_partial_failure_rolls_back_the_original_masked_bytes(self):
        path, args = self.written()
        before = path.read_bytes()

        class FailingOnce(WrittenFileHandles):
            failed = False

            def replace(self, handle, data):
                if not self.failed:
                    self.failed = True
                    super().replace(handle, data[:5])
                    raise OSError("synthetic partial write")
                super().replace(handle, data)

        with self.assertRaises(OSError):
            WrittenFileRestorer(FailingOnce()).restore(args, self.core.restore)
        self.assertEqual(path.read_bytes(), before)

    def test_corrupted_mapping_preserves_masked_file(self):
        path, args = self.written()
        before = path.read_bytes()
        corrupt_records(self.home / "vault" / "a")
        with self.assertRaises((OSError, ValueError, RuntimeError)):
            self.restorer.restore(args, self.core.restore)
        self.assertEqual(path.read_bytes(), before)

    def test_invalid_csv_and_restored_expression_do_not_modify_the_file(self):
        token = self.core.protect(EMAIL)
        for content, restore in ((f'email\n"{token}', self.core.restore),
                                 (f"email\n{token}\n", lambda _: "=1+1")):
            path, args = self.written(content, "result.csv")
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                self.restorer.restore(args, restore)
            self.assertEqual(path.read_bytes(), before)

    def test_absent_file_is_not_created_by_the_post_hook(self):
        path, args = self.written()
        path.unlink()
        with self.assertRaises(OSError):
            self.restorer.restore(args, self.core.restore)
        self.assertFalse(path.exists())

    def test_input_and_restored_size_limits_leave_file_masked(self):
        path, args = self.written()
        before = path.read_bytes()
        with patch("privacy_guard.exports.written_file.MAX_BYTES", 8), self.assertRaises(ValueError):
            self.restorer.restore(args, self.core.restore)
        with patch("privacy_guard.exports.written_file.MAX_BYTES", 2048), self.assertRaises(ValueError):
            self.restorer.restore(args, lambda _: "x" * 2049)
        self.assertEqual(path.read_bytes(), before)
