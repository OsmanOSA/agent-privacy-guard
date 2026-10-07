"""Transactional storage of opaque encrypted BLOBs; never encrypt or decode here.

Interface: batch(), get(key), put_once(key, encrypted). Connections stay open
only within a batch. SQLite serializes writers; committed records are immutable.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

RECORDS_FILE = "personal.sqlite3"


class SqliteRecords:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._connection = None
        self._depth = 0
        self._failed = False

    @contextmanager
    def batch(self):
        self._depth += 1
        try:
            yield
        except BaseException:
            self._failed = True
            raise
        finally:
            self._depth -= 1
            if self._depth == 0:
                connection, self._connection = self._connection, None
                try:
                    if connection is not None:
                        connection.rollback() if self._failed else connection.commit()
                finally:
                    if connection is not None:
                        connection.close()
                    self._failed = False

    def get(self, key: str) -> bytes | None:
        with self.batch():
            connection = self._open(create=False)
            if connection is None:
                return None
            row = connection.execute("SELECT payload FROM records WHERE key = ?", (key,)).fetchone()
            if row is None:
                return None
            if not isinstance(row[0], bytes):
                raise sqlite3.DatabaseError("Invalid encrypted record")
            return row[0]

    def put_once(self, key: str, encrypted: bytes) -> bytes:
        if not isinstance(encrypted, bytes):
            raise sqlite3.DatabaseError("Encrypted payload must be bytes")
        with self.batch():
            connection = self._open(create=True)
            connection.execute("INSERT OR IGNORE INTO records(key, payload) VALUES (?, ?)", (key, encrypted))
            return self.get(key)

    def keys(self, prefix: str) -> list[str]:
        """Enumerate opaque existing keys in one indexed prefix range."""
        with self.batch():
            connection = self._open(create=False)
            if connection is None:
                return []
            return [row[0] for row in connection.execute(
                'SELECT key FROM records WHERE key >= ? AND key < ? ORDER BY key',
                (prefix, prefix + '\uffff'))]

    def _open(self, create: bool):
        if self._connection is not None:
            return self._connection
        existed = self._path.exists()
        if not existed and not create:
            return None
        if create:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        mode = "rw" if existed else "rwc"
        connection = sqlite3.connect(f"{self._path.resolve().as_uri()}?mode={mode}",
                                     uri=True, timeout=2, isolation_level=None)
        try:
            connection.execute("BEGIN IMMEDIATE")
            if not existed:
                connection.execute("CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, payload BLOB NOT NULL)")
                connection.commit()
                connection.execute("BEGIN IMMEDIATE")
        except BaseException:
            connection.close()
            raise
        self._connection = connection
        return connection
