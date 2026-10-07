"""Restore a supported local file only after its ordinary Write has succeeded.

Interface: WrittenFileRestorer(files=None).restore(tool_input, restore) -> bool.
No original text is returned. Match the current bytes to Write's masked content,
pin ancestry, use one exclusive handle, and roll back handled write failures.
"""

from __future__ import annotations

import codecs
from contextlib import ExitStack
from pathlib import Path
from typing import Callable

from privacy_guard.core.category_policy import Mode, mode_for
from privacy_guard.core.tokens import TOKEN_PATTERN
from privacy_guard.exports.csv_content import restore_csv
from privacy_guard.exports.policy import _local_absolute_path, _validated_root
from privacy_guard.exports.written_file_handles import WrittenFileHandles

MAX_BYTES = 2 * 1024 * 1024
_TEXT_EXTENSIONS = frozenset({".txt", ".md", ".markdown", ".csv"})


class WrittenFileRestorer:
    """Restore values inside an already-authorized file without modifying tool arguments."""

    def __init__(self, files: WrittenFileHandles | None = None) -> None:
        self._files = files

    def restore(self, tool_input: object, restore: Callable[[str], str]) -> bool:
        target = _target(tool_input)
        if target is None:
            return False
        expected = tool_input["content"]
        if len(expected.encode("utf-8")) > MAX_BYTES:
            raise ValueError("Local restoration input is too large")
        if not any(mode_for(match.group(1).lower()) is Mode.PSEUDONYMIZE
                   for match in TOKEN_PATTERN.finditer(expected)):
            return False
        files = self._files if self._files is not None else WrittenFileHandles()
        with ExitStack() as held:
            for directory in reversed((target.parent, *target.parent.parents)):
                held.enter_context(files.directory(directory))
            handle = held.enter_context(files.existing_file(target))
            original = files.read(handle, MAX_BYTES)
            text = original.decode("utf-8-sig")
            if text.replace("\r\n", "\n") != expected.replace("\r\n", "\n"):
                raise ValueError("Local file no longer matches the successful Write")
            changed = False

            def restore_value(value):
                nonlocal changed
                result = restore(value)
                changed = changed or result != value
                return result

            restored = restore_csv(text, restore_value) if target.suffix.lower() == ".csv" else restore_value(text)
            if restored is None:
                raise ValueError("Local CSV content is not eligible for restoration")
            if not changed:
                return False
            data = (codecs.BOM_UTF8 if original.startswith(codecs.BOM_UTF8) else b"") + restored.encode("utf-8")
            if len(data) > MAX_BYTES:
                raise ValueError("Restored local file is too large")
            files.validate(handle)
            try:
                files.replace(handle, data)
                files.validate(handle)
            except BaseException:
                files.replace(handle, original)
                raise
        return True


def _target(tool_input: object) -> Path | None:
    if (not isinstance(tool_input, dict) or set(tool_input) != {"file_path", "content"}
            or not isinstance(tool_input["file_path"], str) or not isinstance(tool_input["content"], str)
            or "\x00" in tool_input["content"]):
        return None
    target = _local_absolute_path(tool_input["file_path"])
    if (target is None or target.suffix.lower() not in _TEXT_EXTENSIONS
            or any(part.endswith((".", " ")) for part in target.parts)
            or _validated_root(target.parent) != target.parent):
        return None
    return target
