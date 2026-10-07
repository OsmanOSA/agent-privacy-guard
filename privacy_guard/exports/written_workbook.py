"""Restore a local Excel workbook that a shell command has just produced.

Interface: WorkbookRestorer(files=None).restore(path, restore) -> bool.
Same native guarantees as Write restoration (exports/written_file.py): directories
pinned from the volume root, one exclusive handle, a plain file with one link, and
rollback when the replacement fails. No original value is returned.
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from typing import Callable

from privacy_guard.exports.excel_content import restore_xlsx
from privacy_guard.exports.policy import _local_absolute_path, _validated_root
from privacy_guard.exports.written_file_handles import WrittenFileHandles

MAX_BYTES = 20 * 1024 * 1024
WORKBOOK_EXTENSIONS = frozenset({".xlsx", ".xlsm"})


class WorkbookRestorer:
    """Restore session tokens in the text cells of an existing local workbook."""

    def __init__(self, files: WrittenFileHandles | None = None) -> None:
        self._files = files

    def restore(self, path: str, restore: Callable[[str], str]) -> bool:
        target = _target(path)
        if target is None:
            return False
        files = self._files if self._files is not None else WrittenFileHandles()
        with ExitStack() as held:
            for directory in reversed((target.parent, *target.parent.parents)):
                held.enter_context(files.directory(directory))
            handle = held.enter_context(files.existing_file(target))
            original = files.read(handle, MAX_BYTES)
            changed = False

            def restore_value(value):
                nonlocal changed
                result = restore(value)
                changed = changed or result != value
                return result

            restored = restore_xlsx(original, restore_value)
            if restored is None:
                raise ValueError("Local workbook is not eligible for restoration")
            if not changed:
                return False
            if len(restored) > MAX_BYTES:
                raise ValueError("Restored local workbook is too large")
            files.validate(handle)
            try:
                files.replace(handle, restored)
                files.validate(handle)
            except BaseException:
                files.replace(handle, original)
                raise
        return True


def _target(path: str) -> Path | None:
    target = _local_absolute_path(path)
    # A command that names a missing workbook (failed, or one it only meant to read) is not an error.
    if (target is None or target.suffix.lower() not in WORKBOOK_EXTENSIONS or not target.is_file()
            or any(part.endswith((".", " ")) for part in target.parts)
            or _validated_root(target.parent) != target.parent):
        return None
    return target
