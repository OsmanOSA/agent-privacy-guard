"""Session vaults: where real values stay while the model only sees tokens.

Layout: a directory per session, with an OS-encrypted key and personal records.
New bound records are encrypted BLOBs in SQLite; legacy encrypted files remain
readable without migration. SQLite's visible keys replace the old filenames.

Claude Code runs hook processes in parallel, so every write is atomic and
new personal records are inserted transactionally without replacing a winner.

Interface:
    vaults = VaultStore(root, cipher)
    vault = vaults.session(session_id)
    vault.session_key() / vault.store(token_id, value) / vault.lookup(token_id)
    vaults.close_session(session_id)  # when the agent session ends
"""

from __future__ import annotations

import os
import re
import secrets
import shutil
import tempfile
import time
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from privacy_guard.core.cipher import Cipher
from privacy_guard.core.sqlite_records import RECORDS_FILE, SqliteRecords

DEFAULT_VAULT_ROOT = Path.home() / ".privacy-guard" / "vault"
KEY_FILE = "session.key"
KEY_BYTES = 32
# Session ids become directory names: accept only safe characters (Claude Code uses UUIDs).
SESSION_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,128}")
# A crashed session never signals its end. Its vault is purged after this much
# inactivity: long on purpose, because purging a session that is still open would
# make its tokens unrestorable and leave them written into the user's files.
ABANDONED_AFTER_SECONDS = 7 * 24 * 3600


class VaultError(RuntimeError):
    """The vault cannot be used safely; the hook must fail closed."""


class VaultStore:
    """Every session vault under one root directory, encrypted with one cipher."""

    def __init__(self, root: Path,
                 cipher: Cipher) -> None:
        self._root = root
        self._cipher = cipher

    def session(self, session_id: str) -> SessionVault:
        """Opens the vault of one agent session."""
        return SessionVault(self._session_dir(session_id), self._cipher)

    def close_session(self, session_id: str) -> None:
        """Deletes a finished session's vault, and the vaults of abandoned sessions (PRD §10)."""
        directory = self._session_dir(session_id)
        if directory.exists():
            shutil.rmtree(directory)
        self._purge_abandoned()

    def _session_dir(self, session_id: str) -> Path:
        if not SESSION_ID_PATTERN.fullmatch(session_id):
            raise VaultError("Invalid session id")
        return self._root / session_id

    def _purge_abandoned(self) -> None:
        if not self._root.is_dir():
            return
        cutoff = time.time() - ABANDONED_AFTER_SECONDS
        for directory in self._root.iterdir():
            if directory.is_dir() and _last_activity(directory) < cutoff:
                # Best effort: another session's hook may be touching it right now.
                shutil.rmtree(directory, ignore_errors=True)


class SessionVault:
    """Stores the real values behind the tokens of one agent session."""

    def __init__(self, directory: Path,
                 cipher: Cipher) -> None:
        self._dir = directory
        self._cipher = cipher
        self._key: bytes | None = None
        self._records = SqliteRecords(directory / RECORDS_FILE)

    @contextmanager
    def batch(self):
        """Commit personal mappings before output; keep legacy files unchanged."""
        try:
            with self._records.batch():
                yield
        except sqlite3.Error as error:
            raise VaultError("Encrypted record storage unavailable") from error

    def session_key(self) -> bytes:
        """Returns the session's secret key, creating it on first use."""
        if self._key is None:
            key_file = self._dir / KEY_FILE
            if not key_file.exists():
                self._create_once(key_file, self._cipher.encrypt(secrets.token_bytes(KEY_BYTES)))
            self._key = self._cipher.decrypt(key_file.read_bytes())
        return self._key

    def store(self, token_id: str,
              value: str) -> None:
        """Saves the value behind a token. Idempotent for the same value."""
        with self.batch():
            known = self.lookup(token_id)
            if known is not None and known != value:
                raise VaultError("Token collision")
            if known is None:
                encrypted = self._cipher.encrypt(value.encode("utf-8"))
                if token_id.startswith("bound-"):
                    winner = self._records.put_once(token_id, encrypted)
                    if self._cipher.decrypt(winner).decode("utf-8") != value:
                        raise VaultError("Token collision")
                else:
                    self._write_atomic(self._dir / token_id, encrypted)

    def lookup(self, token_id: str) -> str | None:
        """Returns the value behind a token, or None if this session never issued it."""
        token_file = self._dir / token_id
        with self.batch():
            if token_file.is_file():
                encrypted = token_file.read_bytes()
            elif token_id.startswith("bound-"):
                encrypted = self._records.get(token_id)
            else:
                encrypted = None
            return None if encrypted is None else self._cipher.decrypt(encrypted).decode("utf-8")

    def name_keys(self) -> list[str]:
        """Existing bound person mappings only; include authoritative legacy files."""
        prefix = 'bound-person_name-'
        with self.batch():
            keys = set(self._records.keys(prefix))
            if self._dir.exists():
                keys.update(path.name for path in self._dir.glob(prefix + '*') if path.is_file())
            return sorted(keys)

    def _create_once(self, path: Path,
                     data: bytes) -> None:
        # Write to a temp file, then hard-link it into place: the link fails if
        # another process created the file first, so the first key always wins.
        temp = self._write_temp(data)
        try:
            os.link(temp, path)
        except FileExistsError:
            pass
        finally:
            os.unlink(temp)

    def _write_atomic(self, path: Path,
                      data: bytes) -> None:
        os.replace(self._write_temp(data), path)

    def _write_temp(self, data: bytes) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        handle, name = tempfile.mkstemp(dir=self._dir, prefix=".tmp-")
        with os.fdopen(handle, "wb") as temp:
            temp.write(data)
        return Path(name)


def _last_activity(directory: Path) -> float:
    """Most recent modification time of a vault directory or any file in it."""
    times = [directory.stat().st_mtime] + [entry.stat().st_mtime for entry in directory.iterdir()]
    return max(times)
