"""File-system helpers shared by the installers."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

# A just-stopped service takes a moment to exit and release its files (Windows).
REMOVE_RETRIES = 30
REMOVE_RETRY_DELAY_SECONDS = 0.1


def remove_tree(directory: Path) -> None:
    """Deletes a directory and its content, retrying while Windows still holds a file."""
    for _ in range(REMOVE_RETRIES):
        if not directory.exists():
            return
        try:
            shutil.rmtree(directory)
            return
        except PermissionError:
            time.sleep(REMOVE_RETRY_DELAY_SECONDS)
    shutil.rmtree(directory)
