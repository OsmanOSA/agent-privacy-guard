"""Restore CSV body cells while preserving headers and quoting values correctly.

Interface: restore_csv(content, restore) -> str | None. None rejects the content.
This module validates text only; it does not authorize or write a destination.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Callable

_NUMERIC_TEXT = re.compile(r"[+-]?\d[\d .()-]*")


def restore_csv(content: str, restore: Callable[[str], str]) -> str | None:
    rows = _rows(content)
    if rows is None:
        return None
    restored = [rows[0]] + [[restore(cell) for cell in row] for row in rows[1:]]
    if not all(_data_cell(cell) for row in restored for cell in row):
        return None
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\r\n").writerows(restored)
    return output.getvalue()


def _data_cell(value: str) -> bool:
    if "\x00" in value:
        return False
    stripped = value.lstrip(" \t\r\n")
    if stripped.startswith(("=", "+", "-", "@")):
        return bool(_NUMERIC_TEXT.fullmatch(stripped))
    return True


def _rows(content: str) -> list[list[str]] | None:
    try:
        rows = list(csv.reader(io.StringIO(content, newline=""), strict=True))
    except csv.Error:
        return None
    if len(rows) < 2 or not rows[0] or any(not cell.strip() for cell in rows[0]):
        return None
    if any(len(row) != len(rows[0]) for row in rows):
        return None
    return rows if all(_data_cell(cell) for row in rows for cell in row) else None
