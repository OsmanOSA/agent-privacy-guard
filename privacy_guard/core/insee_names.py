"""Optional INSEE complement for explicitly personal fields and attribution phrases.

The lexicon never vetoes NER/rule findings. Bare dictionary words, identifiers
and paths do not trigger it. Recognition still depends on context and coverage.
"""

from __future__ import annotations

import re
from pathlib import Path

from privacy_guard.core.file_names import FileNameDetector
from privacy_guard.core.findings import Finding
from privacy_guard.core.name_detector import CombinedNameDetector, HeuristicNameDetector
from privacy_guard.core.name_lexicon import LEXICON_FILE, NameLexicon

_GIVEN = r'pr[ée]noms?|first[ _]name|given[ _]name'
_FAMILY = r'nom de famille|nom de naissance|last[ _]name|surname|family[ _]name'
_FULL = r'nom(?: complet)?|full[ _]name'
_BY = r'sign[ée] par|r[ée]dig[ée] par|written by|reported by|authored by'
_CONTEXT = re.compile(
    rf'(?<![\w])(?:(?P<given>{_GIVEN})|(?P<family>{_FAMILY})|(?P<full>{_FULL}))'
    rf'["\']?[ \t]*[:=][ \t]*["\']?|(?P<by>\b(?:{_BY}))[ \t]+', re.I,
)
_LETTER = r'[^\W\d_][\u0300-\u036f]*'
_WORD = rf'(?:{_LETTER})+(?:[\x27’\-](?:{_LETTER})+)*'
_VALUE = re.compile(rf'(?P<value>{_WORD}(?:[ \t]+{_WORD}){{0,3}})(?=$|["\',;\n\r.)\]}}!?])')


def has_person_context(text: str) -> bool:
    """Permit lowercase personal fields through the existing fast capital gate."""
    return _CONTEXT.search(text) is not None


class InseeNameDetector:
    def __init__(self, path: Path) -> None:
        self.lexicon = NameLexicon(path)

    def find_names(self, text: str) -> list[Finding]:
        candidates = []
        for context in _CONTEXT.finditer(text):
            value = _VALUE.match(text, context.end())
            if value:
                candidates.append((context.lastgroup, value))
        if not candidates:
            return []
        with self.lexicon.reader() as contains:
            return [Finding('person_name', value.start('value'), value.end('value'))
                    for kind, value in candidates if _known(contains, kind, value.group('value'))]


def _known(contains, kind: str, value: str) -> bool:
    if kind in {'given', 'family'}:
        return contains(kind, value)
    if kind == 'full' and (contains('given', value) or contains('family', value)):
        return True
    words = value.split()
    return any(contains('given', ' '.join(words[:i])) and contains('family', ' '.join(words[i:]))
               for i in range(1, len(words)))


def local_name_detector(guard_home: Path | None = None):
    """An explicit local index adds context rules; its absence keeps the baseline."""
    path = (guard_home or Path.home() / '.privacy-guard') / 'data' / LEXICON_FILE
    heuristic = HeuristicNameDetector()
    if not path.is_file():
        return heuristic
    return CombinedNameDetector([heuristic, InseeNameDetector(path), FileNameDetector(NameLexicon(path))])
