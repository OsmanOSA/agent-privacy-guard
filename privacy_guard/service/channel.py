"""The private channel between the hook and the background service.

A Windows named pipe or a Unix socket, from the standard library
(multiprocessing.connection), authenticated with a secret key that only the
user's files hold: no other program can query the service.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_RUN_DIR = Path.home() / ".privacy-guard" / "run"
KEY_FILE = "service.key"
SOCKET_FILE = "service.sock"
KEY_BYTES = 32


@dataclass(frozen=True)
class ServiceChannel:
    """Where the service listens and the key both sides must present."""

    run_dir: Path

    @property
    def family(self) -> str:
        return "AF_PIPE" if sys.platform == "win32" else "AF_UNIX"

    @property
    def address(self) -> str:
        if sys.platform == "win32":
            # One pipe per run directory, so tests never reach the user's real service.
            digest = hashlib.sha256(str(self.run_dir.resolve()).encode()).hexdigest()[:16]
            return rf"\\.\pipe\privacy-guard-{digest}"
        return str(self.run_dir / SOCKET_FILE)

    def authkey(self) -> bytes:
        """Returns the shared secret, creating it on first use."""
        key_file = self.run_dir / KEY_FILE
        if not key_file.exists():
            self._create_key(key_file)
        return key_file.read_bytes()

    def _create_key(self, key_file: Path) -> None:
        # Temp file + hard link: if the hook and the service race, the first key wins.
        self.run_dir.mkdir(parents=True, exist_ok=True)
        handle, temp = tempfile.mkstemp(dir=self.run_dir, prefix=".tmp-")
        with os.fdopen(handle, "wb") as file:
            file.write(secrets.token_bytes(KEY_BYTES))
        try:
            os.link(temp, key_file)
        except FileExistsError:
            pass
        finally:
            os.unlink(temp)
