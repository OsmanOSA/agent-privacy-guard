"""Splits a delimited line into fields, keeping each field's position in the text.

The csv module returns values only; detection needs where each value sits, to
replace it in place. Quotes protect delimiters inside a value and are not part
of the reported value.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    """A value's span in the original text, without surrounding spaces and quotes."""

    start: int
    end: int

    def value(self, text: str) -> str:
        return text[self.start:self.end]


def split_fields(text: str,
                 start: int,
                 end: int,
                 delimiter: str,
                 quotes: str = "\"'") -> list[Field]:
    """Fields of text[start:end], separated by `delimiter` outside quotes."""
    fields, field_start, open_quote = [], start, None
    for position in range(start, end):
        character = text[position]
        if open_quote:
            if character == open_quote:
                open_quote = None  # a doubled quote ('') reopens just after: same result
        elif character in quotes:
            open_quote = character
        elif character == delimiter:
            fields.append(_trimmed(text, field_start, position, quotes))
            field_start = position + 1
    fields.append(_trimmed(text, field_start, end, quotes))
    return fields


def _trimmed(text: str,
             start: int,
             end: int,
             quotes: str) -> Field:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if end - start >= 2 and text[start] in quotes and text[end - 1] == text[start]:
        start, end = start + 1, end - 1
    return Field(start, end)
