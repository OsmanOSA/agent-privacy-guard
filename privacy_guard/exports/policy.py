"""Authorize personal-value restoration into one new local CSV or SQL export.

Interface: destination(path) -> Path | None; restore_input(data, restore) -> dict | None.
Only data is prepared for restoration (CSV body cells, SQL literals and comments);
paths and headers are unchanged.
The local writer owns the actual write. This policy alone does not enforce egress.
"""

from __future__ import annotations

import ctypes
import json
import ntpath
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from privacy_guard.exports.file_content import restore_text

_EXPORT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:csv|sql)", re.IGNORECASE)
_DEVICES = frozenset({"CON", "PRN", "AUX", "NUL"} | {f"{prefix}{i}" for prefix in ("COM", "LPT") for i in range(1, 10)})


@dataclass(frozen=True)
class CsvExportPolicy:
    """A user-selected directory; no selection disables all restoration."""

    root: Path | None = None

    @classmethod
    def from_file(cls, path: Path) -> CsvExportPolicy:
        """Load local configuration; malformed configuration fails the export command."""
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return cls()
        if (not isinstance(config, dict) or set(config) != {"version", "root"}
                or type(config["version"]) is not int or config["version"] != 1):
            raise ValueError("Invalid CSV export policy")
        if config["root"] is None:
            return cls()
        if not isinstance(config["root"], str):
            raise ValueError("Invalid CSV export root")
        root = _local_absolute_path(config["root"])
        if root is None or _validated_root(root) is None:
            raise ValueError("CSV export root must be an existing local directory without links")
        return cls(root)

    def restore_input(self, tool_input: object, restore: Callable[[str], str]) -> dict | None:
        """Prepare CSV or SQL data for the local writer, or None when ineligible."""
        if not isinstance(tool_input, dict) or set(tool_input) != {"file_path", "content"}:
            return None
        target = self.destination(tool_input["file_path"])
        if target is None or not isinstance(tool_input["content"], str):
            return None
        content = restore_text(target.name, tool_input["content"], restore)
        return None if content is None else {"file_path": str(target), "content": content}

    def destination(self, filename: object) -> Path | None:
        if self.root is None or not isinstance(filename, str):
            return None
        root = _validated_root(self.root)
        target = _local_absolute_path(filename)
        if root is None or target is None or target.parent != root:
            return None
        if not _EXPORT_NAME.fullmatch(target.name) or target.name.split(".")[0].upper() in _DEVICES:
            return None
        try:
            target.lstat()
        except FileNotFoundError:
            return target
        except OSError:
            return None
        # No overwrites: existing files, links and hard links are outside this step.
        return None


def _local_absolute_path(value: str) -> Path | None:
    if not value or "\x00" in value or value.startswith(("\\", "//")):
        return None
    drive, tail = ntpath.splitdrive(value)
    if ":" in tail or (drive and not re.fullmatch(r"[A-Za-z]:", drive)):
        return None
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        return None
    return path


def _fixed_local_drive(path: Path) -> bool:
    if sys.platform != "win32":
        return True  # Portable tests do not establish support for another platform.
    get_type = ctypes.WinDLL("kernel32", use_last_error=True).GetDriveTypeW
    get_type.argtypes = [ctypes.c_wchar_p]
    get_type.restype = ctypes.c_uint
    return get_type(path.anchor) == 3  # DRIVE_FIXED; mapped network drives are rejected.


def _validated_root(root: Path) -> Path | None:
    if _local_absolute_path(str(root)) is None or not _fixed_local_drive(root):
        return None
    try:
        for part in (root, *root.parents):
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                return None
        return root.resolve(strict=True) if root.is_dir() else None
    except (OSError, RuntimeError):
        return None
