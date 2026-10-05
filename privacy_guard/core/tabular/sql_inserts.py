"""Personal columns of SQL INSERT statements: INSERT INTO t (col, ...) VALUES (...), (...);

The column list says which values are personal, in every row of the statement.
"""

from __future__ import annotations

import re

from privacy_guard.core.findings import Finding
from privacy_guard.core.tabular.columns import personal_columns
from privacy_guard.core.tabular.fields import split_fields

_INSERT = re.compile(
    r"\bINSERT\s+INTO\s+[\w.`\"\[\]]+\s*\((?P<columns>[^()]*)\)\s*VALUES\s*(?P<rows>(?:\((?:[^()']|'(?:[^']|'')*')*\)\s*,?\s*)+)",
    re.IGNORECASE,
)
# One row: parentheses, with quoted strings that may themselves hold parentheses.
_ROW = re.compile(r"\((?:[^()']|'(?:[^']|'')*')*\)")
_NULL = re.compile(r"null", re.IGNORECASE)


def find_in_sql_inserts(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for statement in _INSERT.finditer(text):
        column_fields = split_fields(text, statement.start("columns"), statement.end("columns"), ",", "`\"")
        kinds = personal_columns([field.value(text) for field in column_fields])
        if not kinds:
            continue
        for row in _ROW.finditer(text, statement.start("rows"), statement.end("rows")):
            values = split_fields(text, row.start() + 1, row.end() - 1, ",", "'")
            findings += [
                Finding(kind, values[index].start, values[index].end)
                for index, kind in kinds.items()
                if index < len(values) and _is_value(values[index].value(text))
            ]
    return findings


def _is_value(value: str) -> bool:
    return bool(value) and not _NULL.fullmatch(value)
