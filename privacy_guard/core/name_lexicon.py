"""Read-only public name index; lookup candidates, never load the whole dictionary."""

from __future__ import annotations

import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path

LEXICON_FILE = 'insee-names.sqlite'
SCHEMA_VERSION = 1


def normalize(value: str) -> str:
    """Case/accent folding is for matching only; original spans stay unchanged."""
    value = unicodedata.normalize('NFKD', value.replace('’', "'")).casefold()
    return ' '.join(''.join(c for c in value if not unicodedata.combining(c)).split())


class NameLexicon:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def reader(self):
        # Read-only also prevents SQLite from creating an empty file on deletion.
        db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True)
        try:
            if db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
                raise ValueError('Unsupported public name lexicon format')
            yield lambda kind, value: db.execute(
                'SELECT 1 FROM names WHERE kind=? AND value=?',
                (kind, normalize(value)),
            ).fetchone() is not None
        finally:
            db.close()
