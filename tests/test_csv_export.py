import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from privacy_guard.exports.policy import CsvExportPolicy
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from tests.fakes import ReversingCipher, STRIPE_KEY

EMAIL = "jean.dupont@example.com"


class CsvExportPolicyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve()
        self.root = self.home / "exports"
        self.root.mkdir()
        self.policy = CsvExportPolicy(self.root)
        self.core = PrivacyCore(VaultStore(self.home / "vault", ReversingCipher()).session("a"), HeuristicNameDetector())
        self.token = self.core.protect(EMAIL)
        self.args = {"file_path": str(self.root / "clients.csv"), "content": f"email\n{self.token}\n"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_restores_only_body_cells_of_new_csv(self):
        result = self.policy.restore_input(self.args, self.core.restore)

        self.assertEqual(result["file_path"], self.args["file_path"])
        self.assertEqual(list(csv.reader(io.StringIO(result["content"]))), [["email"], [EMAIL]])

    def test_sql_export_restores_literals_only(self):
        args = {"file_path": str(self.root / "seed.sql"),
                "content": f"INSERT INTO t VALUES ('{self.token}'); -- {self.token}\nSELECT {self.token};\n"}
        result = self.policy.restore_input(args, self.core.restore)
        self.assertEqual(result["content"], f"INSERT INTO t VALUES ('{EMAIL}'); -- {EMAIL}\nSELECT {self.token};\n")

    def test_default_policy_does_not_lookup_values(self):
        restore = Mock()
        self.assertIsNone(CsvExportPolicy().restore_input(self.args, restore))
        restore.assert_not_called()

    def test_rejected_destination_does_not_lookup_values(self):
        restore = Mock()
        paths = [str(self.home / "outside.csv"), "relative.csv", "https://example.invalid/x.csv",
                 r"\\server\share\clients.csv", r"\\?\C:\clients.csv", r"\\.\C:\clients.csv",
                 str(self.root / "clients.csv:stream"), str(self.root / "../exports/clients.csv"),
                 str(self.root / "clients.json"), str(self.root / "CON.csv"),
                 str(self.root / f"{self.token}.csv")]
        for filename in paths:
            with self.subTest(filename=filename):
                self.assertIsNone(self.policy.restore_input({**self.args, "file_path": filename}, restore))
        restore.assert_not_called()

    def test_nested_export_and_existing_file_do_not_restore(self):
        nested = self.root / "nested"
        nested.mkdir()
        existing = self.root / "existing.csv"
        existing.write_text("existing", encoding="utf-8")
        for target in (nested / "clients.csv", existing):
            with self.subTest(target=target):
                self.assertIsNone(self.policy.restore_input({**self.args, "file_path": str(target)}, self.core.restore))
        self.assertEqual(existing.read_text(encoding="utf-8"), "existing")

    def test_rechecks_directory_before_releasing_values(self):
        self.root.rmdir()
        self.assertIsNone(self.policy.restore_input(self.args, self.core.restore))

    def test_mapped_network_drive_is_rejected(self):
        with patch("privacy_guard.exports.policy._fixed_local_drive", return_value=False):
            self.assertIsNone(self.policy.restore_input(self.args, self.core.restore))

    def test_reparse_directory_is_rejected(self):
        info = self.root.stat()
        linked = Mock(st_mode=info.st_mode, st_file_attributes=0x400)
        with patch.object(Path, "lstat", return_value=linked):
            self.assertIsNone(self.policy.restore_input(self.args, self.core.restore))

    def test_symlink_target_or_directory_is_rejected(self):
        outside = self.home / "outside.csv"
        outside.write_text("outside", encoding="utf-8")
        target = self.root / "clients.csv"
        alias = self.home / "alias"
        try:
            target.symlink_to(outside)
            alias.symlink_to(self.root, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"Creating symlinks is unavailable: {error}")
        self.assertIsNone(self.policy.restore_input(self.args, self.core.restore))
        alias_args = {**self.args, "file_path": str(alias / "new.csv")}
        self.assertIsNone(CsvExportPolicy(alias).restore_input(alias_args, self.core.restore))

    def test_malformed_csv_and_unexpected_arguments_do_not_lookup_values(self):
        restore = Mock()
        for content in ('email\n"unterminated', "email,phone\none\n", "email\n", "\nvalue\n", "email\na\x00b\n"):
            self.assertIsNone(self.policy.restore_input({**self.args, "content": content}, restore))
        for args in (None, {"file_path": self.args["file_path"]}, {**self.args, "extra": True}, {**self.args, "content": 1}):
            self.assertIsNone(self.policy.restore_input(args, restore))
        restore.assert_not_called()

    def test_quotes_restored_commas_quotes_and_newlines(self):
        original = 'Jean, "Dupont"\nSecond line'
        result = self.policy.restore_input(self.args, lambda _: original)
        self.assertEqual(list(csv.reader(io.StringIO(result["content"]))), [["email"], [original]])

    def test_headers_never_restore(self):
        result = self.policy.restore_input({**self.args, "content": f"{self.token}\n{self.token}\n"}, self.core.restore)
        self.assertEqual(list(csv.reader(io.StringIO(result["content"]))), [[self.token], [EMAIL]])

    def test_redacted_secrets_remain_redacted(self):
        marker = self.core.protect(STRIPE_KEY)
        result = self.policy.restore_input({**self.args, "content": f"credential\n{marker}\n"}, self.core.restore)
        self.assertEqual(list(csv.reader(io.StringIO(result["content"]))), [["credential"], [marker]])

    def test_foreign_session_token_remains_masked(self):
        other = PrivacyCore(VaultStore(self.home / "other", ReversingCipher()).session("b"), HeuristicNameDetector())
        token = other.protect(EMAIL)
        result = self.policy.restore_input({**self.args, "content": f"email\n{token}\n"}, self.core.restore)
        self.assertNotIn(EMAIL, result["content"])
        self.assertIn(token, result["content"])

    def test_spreadsheet_expression_cannot_receive_restored_values(self):
        restore = Mock()
        for value in ("=1+1", " +cmd|'test'!A0", "@SUM(1)", "\t=1+1"):
            self.assertIsNone(self.policy.restore_input({**self.args, "content": f"value\n{value}\n"}, restore))
        restore.assert_not_called()
        self.assertIsNone(self.policy.restore_input(self.args, lambda _: '=WEBSERVICE("https://example.invalid")'))

    def test_phone_and_negative_number_text_can_be_exported(self):
        for value in ("+33 6 12 34 56 78", "-42"):
            result = self.policy.restore_input(self.args, lambda _: value)
            self.assertEqual(list(csv.reader(io.StringIO(result["content"])))[1], [value])

    def test_policy_loading_missing_disabled_and_valid_configuration(self):
        config = self.home / "export-policy.json"
        self.assertIsNone(CsvExportPolicy.from_file(config).root)
        config.write_text(json.dumps({"version": 1, "root": None}), encoding="utf-8")
        self.assertIsNone(CsvExportPolicy.from_file(config).root)
        config.write_text(json.dumps({"version": 1, "root": str(self.root)}), encoding="utf-8")
        self.assertEqual(CsvExportPolicy.from_file(config).root, self.root)

    def test_invalid_configuration_fails_instead_of_enabling_another_root(self):
        config = self.home / "export-policy.json"
        for value in ([], {"version": 2, "root": str(self.root)}, {"version": True, "root": str(self.root)},
                      {"version": 1, "root": "relative"}, {"version": 1, "root": 5},
                      {"version": 1, "root": str(self.home / "missing")},
                      {"version": 1, "root": str(self.root), "extra": True}):
            config.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(ValueError):
                CsvExportPolicy.from_file(config)
        config.write_text("not-json", encoding="utf-8")
        with self.assertRaises(ValueError):
            CsvExportPolicy.from_file(config)
