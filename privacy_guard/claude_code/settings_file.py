"""Access to the Claude Code settings.json file."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

BACKUP_SUFFIX = "privacy-guard-backup"


class SettingsFile:
    """Reads and writes settings.json, with a timestamped backup before every write."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict:
        """Returns the file content, or an empty dict if the file does not exist."""
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def save(self, settings: dict) -> Path | None:
        """Writes the settings and returns the backup path (None if there was no file)."""
        backup = self._backup()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
        self._path.write_text(content, encoding="utf-8")
        return backup

    def _backup(self) -> Path | None:
        if not self._path.exists():
            return None
        backup = self._unused_backup_path()
        shutil.copy2(self._path, backup)
        return backup

    def _unused_backup_path(self) -> Path:
        # The clock alone is not enough: on Windows two writes can share the same
        # microsecond. A counter guarantees a backup is never overwritten.
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        base = f"{self._path.name}.{BACKUP_SUFFIX}-{stamp}"
        candidate = self._path.with_name(base)
        counter = 1
        while candidate.exists():
            candidate = self._path.with_name(f"{base}-{counter}")
            counter += 1
        return candidate
