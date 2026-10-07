"""Restore and write a CSV while its destination ancestry is pinned.

Interface: CsvWriter(policy).write(filename, masked_csv, restore) -> None.
The writer never returns original content or creates an output directory.
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from typing import Callable

from privacy_guard.exports.policy import CsvExportPolicy
from privacy_guard.exports.windows_files import WindowsFiles


class CsvWriter:
    """Keep authorization, restoration and exclusive writing in one local operation."""

    def __init__(self, policy: CsvExportPolicy, files: WindowsFiles | None = None) -> None:
        self._policy = policy
        self._files = files if files is not None else WindowsFiles()

    def write(self, filename: str, content: str, restore: Callable[[str], str]) -> None:
        if self._policy.root is None or Path(filename).name != filename:
            raise ValueError("A configured directory and a plain CSV filename are required")
        args = {"file_path": str(self._policy.root / filename), "content": content}
        target = self._policy.destination(args["file_path"])
        if target is None:
            raise ValueError("CSV export destination is not authorized")
        with ExitStack() as directories:
            # Open from the volume root downward, checking each pinned object.
            for directory in reversed((target.parent, *target.parent.parents)):
                directories.enter_context(self._files.directory(directory))
            prepared = self._policy.restore_input(args, restore)
            if prepared is None or Path(prepared["file_path"]) != target:
                raise ValueError("CSV export content or destination is not authorized")
            with self._files.new_file(target) as handle:
                self._files.write(handle, prepared["content"].encode("utf-8"))
