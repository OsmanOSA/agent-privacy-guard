"""Personal columns of CSV-like tables: CSV, TSV, semicolon files, Markdown tables.

A table is a header line that names at least one personal column, followed by
rows with the same number of fields, until a blank line or a line of another shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from privacy_guard.core.findings import Finding
from privacy_guard.core.tabular.columns import personal_columns
from privacy_guard.core.tabular.fields import Field, split_fields

DELIMITERS = (",", ";", "\t", "|")
# A column name: words, digits, spaces, dots, slashes, dashes; not a sentence.
_COLUMN_NAME = re.compile(r"[\w ./-]{1,40}")
# The line under a Markdown table header: |---|:---:|
_MARKDOWN_SEPARATOR = re.compile(r"[\s|:-]+")
# Cheap test before splitting a line: a header must contain one of these stems.
# Most lines of code or prose fail it, which keeps the scan fast on large outputs.
_PERSONAL_COLUMN_STEM = re.compile(r"name|nom|birth|naissance|dob|address|adresse|street", re.IGNORECASE)


@dataclass(frozen=True)
class _Header:
    delimiter: str
    width: int  # number of fields every row must have
    kinds: dict[int, str]  # personal column index -> finding kind


def find_in_csv_tables(text: str) -> list[Finding]:
    lines = _line_spans(text)
    findings: list[Finding] = []
    index = 0
    while index < len(lines):
        header = _header(text, *lines[index])
        index += 1
        if header is None:
            continue
        while index < len(lines):
            fields = split_fields(text, *lines[index], header.delimiter)
            if len(fields) != header.width or not text[slice(*lines[index])].strip():
                break  # the table ends with a blank line or a line of another shape
            if not _MARKDOWN_SEPARATOR.fullmatch(text[slice(*lines[index])]):
                findings += _personal_values(fields, header.kinds)
            index += 1
    return findings


def _header(text: str,
            start: int,
            end: int) -> _Header | None:
    """The header described by a line, or None if the line does not name personal columns."""
    if not _PERSONAL_COLUMN_STEM.search(text, start, end):
        return None
    for delimiter in DELIMITERS:
        fields = split_fields(text, start, end, delimiter)
        names = [field.value(text) for field in fields]
        if len(fields) < 2 or not all(_COLUMN_NAME.fullmatch(name) for name in names if name):
            continue
        kinds = personal_columns(names)
        if kinds:
            return _Header(delimiter, len(fields), kinds)
    return None


def _personal_values(fields: list[Field],
                     kinds: dict[int, str]) -> list[Finding]:
    return [Finding(kind, fields[index].start, fields[index].end)
            for index, kind in kinds.items() if fields[index].end > fields[index].start]


def _line_spans(text: str) -> list[tuple[int, int]]:
    spans, start = [], 0
    for match in re.finditer(r"\r?\n", text):
        spans.append((start, match.start()))
        start = match.end()
    spans.append((start, len(text)))
    return spans
