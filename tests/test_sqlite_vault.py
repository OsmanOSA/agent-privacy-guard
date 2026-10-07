"""Encrypted payloads, legacy preservation and concurrent immutable inserts."""

import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Barrier

from privacy_guard.core.bound_values import BoundValues
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.sqlite_records import RECORDS_FILE
from privacy_guard.core.tokens import format_token, token_id
from privacy_guard.core.vault import VaultError, VaultStore
from tests.fakes import ReversingCipher
from tests.vault_storage import encrypted_record

EMAIL = "alice.martin@example.com"
IDENTIFIER = "ABCD1234"


class SqliteVaultTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cipher = ReversingCipher()
        self.vaults = VaultStore(self.root, self.cipher)
        self.vault = self.vaults.session("a")

    def tearDown(self):
        self.temp.cleanup()

    def test_only_encrypted_payloads_enter_database(self):
        BoundValues(self.vault).store("email", IDENTIFIER, EMAIL)
        database = self.root / "a" / RECORDS_FILE
        self.assertNotIn(EMAIL.encode(), database.read_bytes())
        payload = encrypted_record(database.parent, "bound-email-" + IDENTIFIER)
        self.assertTrue(payload.startswith(ReversingCipher.PREFIX))
        self.assertEqual(json.loads(self.cipher.decrypt(payload))["value"], EMAIL)

    def test_failed_batch_rolls_back_and_can_be_retried(self):
        values = BoundValues(self.vault)
        with self.assertRaises(RuntimeError):
            with self.vault.batch():
                values.store("email", IDENTIFIER, EMAIL)
                raise RuntimeError("Interrupted operation")
        self.assertIsNone(values.lookup("email", IDENTIFIER))
        values.store("email", IDENTIFIER, EMAIL)
        self.assertEqual(values.lookup("email", IDENTIFIER), EMAIL)

    def test_corrupted_database_is_not_an_unknown_token(self):
        values = BoundValues(self.vault)
        values.store("email", IDENTIFIER, EMAIL)
        (self.root / "a" / RECORDS_FILE).write_bytes(b"corrupted database")
        with self.assertRaises(VaultError):
            values.lookup("email", IDENTIFIER)

    def test_locked_database_fails_without_overwriting_records(self):
        values = BoundValues(self.vault)
        values.store("email", IDENTIFIER, EMAIL)
        with closing(sqlite3.connect(self.root / "a" / RECORDS_FILE)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            with self.assertRaises(VaultError):
                values.store("email", IDENTIFIER, "other@example.com")
            connection.rollback()
        self.assertEqual(values.lookup("email", IDENTIFIER), EMAIL)

    def test_legacy_bound_files_and_session_key_are_preserved(self):
        directory = self.root / "a"
        directory.mkdir()
        key = b"K" * 32
        (directory / "session.key").write_bytes(self.cipher.encrypt(key))
        identifier = token_id(key, EMAIL)
        record = {"version": 1, "kind": "email", "identifier": identifier, "value": EMAIL}
        encoded = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode()
        (directory / ("bound-email-" + identifier)).write_bytes(self.cipher.encrypt(encoded))
        before = {p.name: p.read_bytes() for p in directory.iterdir()}
        core = PrivacyCore(self.vault, HeuristicNameDetector())
        token = format_token("email", identifier)
        self.assertEqual(core.restore(token), EMAIL)
        self.assertEqual(core.protect(EMAIL), token)
        self.assertEqual({p.name: p.read_bytes() for p in directory.iterdir()}, before)
        core.protect("new.person@example.com")
        for name, content in before.items():
            self.assertEqual((directory / name).read_bytes(), content)
        self.assertEqual(core.restore(token), EMAIL)

    def test_concurrent_identical_inserts_keep_one_record(self):
        barrier = Barrier(4)

        def write(_):
            values = BoundValues(self.vaults.session("a"))
            barrier.wait()
            values.store("email", IDENTIFIER, EMAIL)
            return values.lookup("email", IDENTIFIER)

        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(write, range(4))), [EMAIL] * 4)
        with closing(sqlite3.connect(self.root / "a" / RECORDS_FILE)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM records").fetchone()[0], 1)

    def test_concurrent_collision_never_replaces_the_winner(self):
        barrier = Barrier(2)

        def write(value):
            values = BoundValues(self.vaults.session("a"))
            barrier.wait()
            try:
                values.store("email", IDENTIFIER, value)
                return value
            except VaultError:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(write, [EMAIL, "other@example.com"]))
        winners = [value for value in outcomes if value is not None]
        self.assertEqual(len(winners), 1)
        self.assertEqual(BoundValues(self.vault).lookup("email", IDENTIFIER), winners[0])


if __name__ == "__main__":
    unittest.main()
