"""Annotated corpus documents.

In a corpus file, every value that must be hidden is written ⟪category:value⟫,
e.g. ⟪name:Jean Dupont⟫. Parsing removes the markup and records where each
value sits in the clean text, which is what the detectors are run on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# ⟪ and ⟫ (U+27EA, U+27EB): never used by the documents themselves, and distinct
# from the ⟦ ⟧ of Privacy Guard's tokens.
MARKUP = re.compile("⟪(?P<category>[a-z_]+):(?P<value>.*?)⟫", re.DOTALL)
CATEGORIES = frozenset(
    {"name", "email", "phone", "address", "birth_date", "identifier", "banking", "secret"}
)


@dataclass(frozen=True)
class Expected:
    """A value the detectors must hide."""

    category: str
    start: int
    end: int


@dataclass(frozen=True)
class AnnotatedDocument:
    name: str
    text: str
    expected: tuple[Expected, ...]


def parse(name: str,
          source: str) -> AnnotatedDocument:
    """Strips the markup of one document and locates every expected value."""
    pieces, expected, cursor, length = [], [], 0, 0
    for match in MARKUP.finditer(source):
        category, value = match.group("category"), match.group("value")
        if category not in CATEGORIES:
            raise ValueError(f"{name}: unknown category {category!r}")
        before = source[cursor:match.start()]
        pieces += [before, value]
        start = length + len(before)
        expected.append(Expected(category, start, start + len(value)))
        length = start + len(value)
        cursor = match.end()
    pieces.append(source[cursor:])
    return AnnotatedDocument(name, "".join(pieces), tuple(expected))


def load_corpus(directory: Path) -> list[AnnotatedDocument]:
    """Every file of the corpus directory, in name order."""
    return [parse(path.name, path.read_text(encoding="utf-8"))
            for path in sorted(directory.iterdir()) if path.is_file()]
