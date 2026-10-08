"""Restore a file's text according to its format.

Interface: restore_text(name, text, restore) -> str | None. None rejects the content.
CSV restores body cells only (exports/csv_content.py), SQL its literals and comments
with SQL escaping (exports/sql_content.py), every other text format the whole text.
"""

from __future__ import annotations

from pathlib import PurePath
from typing import Callable

from privacy_guard.exports.csv_content import restore_csv
from privacy_guard.exports.sql_content import restore_sql

_FORMATS = {".csv": restore_csv, ".sql": restore_sql}


def restore_text(name: str, text: str, restore: Callable[[str], str]) -> str | None:
    restorer = _FORMATS.get(PurePath(name).suffix.lower())
    return restorer(text, restore) if restorer is not None else restore(text)
