"""Inspect or tamper with synthetic encrypted record fixtures, never user vaults."""

import sqlite3
from contextlib import closing

from privacy_guard.core.sqlite_records import RECORDS_FILE


def encrypted_record(directory, key):
    with closing(sqlite3.connect(directory / RECORDS_FILE)) as connection:
        return connection.execute("SELECT payload FROM records WHERE key = ?", (key,)).fetchone()[0]


def move_record(directory, old_key, new_key):
    with closing(sqlite3.connect(directory / RECORDS_FILE)) as connection, connection:
        connection.execute("UPDATE records SET key = ? WHERE key = ?", (new_key, old_key))


def corrupt_records(directory):
    for path in directory.glob("bound-*"):
        path.write_bytes(b"corrupt")
    database = directory / RECORDS_FILE
    if database.exists():
        database.write_bytes(b"corrupt")
