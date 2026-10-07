"""Person names spelled inside file names: cv_camille_lefebvre.md, contrat-dupont-marie.pdf.

Glob, ls or git output list such files, and the name in them is as personal as in the
document. A pair of adjacent words in a file name is a name when the public INSEE index
knows one as a given name and the other as a family name, in either order.

That index also lists developer words ("test", "data", "read" as given names, "main",
"report" as family names), so test_data.py would match: such words never count. They
come from the measured identifier vocabulary of core/code_words.py (2.2% of 30,000 real
file names matched without it, 0.3% with it), plus file words it misses.

Interface:
    FileNameDetector(lexicon).find_names(text) -> list[Finding]
    has_file_name(text) -> bool    lets lowercase listings reach name detection
"""

from __future__ import annotations

import re

from privacy_guard.core.code_words import CODE_WORDS
from privacy_guard.core.findings import Finding
from privacy_guard.core.name_lexicon import NameLexicon
from privacy_guard.core.tool_vocabulary import is_tool_vocabulary

# A file name with an extension, as listed by tools: no spaces or path separators.
_FILE_NAME = re.compile(r"[^\s/\\:*?\"<>|]+\.[A-Za-z0-9]{1,8}(?![\w])")
# Alphabetic parts of three letters or more (Unicode letters, no digits or underscore).
_PART = re.compile(r"[^\W\d_]{3,}")
_SEPARATORS = frozenset({"_", "-"})
# Words of technical file names that the INSEE index also lists as names and that
# Python's own identifiers do not use often enough to be in CODE_WORDS.
_FILE_WORDS = frozenset("""
    admin app assets auth backup base bench build cache chart client code common config
    controller core cuda data debug demo dev dist doc docs draft dummy error event example export
    file final fixture fixtures form handler helper image import index item job key layout
    lib list load loader log main manager message mock model module note notes order page
    patch plugin product profile public read report router sample schema script server
    service session setup source spec start state static style table task temp test tests
    theme tool tools type update user util utils view worker write
""".split()) | CODE_WORDS


def has_file_name(text: str) -> bool:
    return _FILE_NAME.search(text) is not None


class FileNameDetector:
    """Given and family name pairs inside file names, confirmed by the INSEE index."""

    def __init__(self, lexicon: NameLexicon) -> None:
        self._lexicon = lexicon

    def find_names(self, text: str) -> list[Finding]:
        pairs = list(_candidate_pairs(text))
        if not pairs:
            return []
        with self._lexicon.reader() as contains:
            return [Finding("person_name", first.start(), second.end()) for first, second in pairs
                    if _is_name(contains, first.group(), second.group())]


def _candidate_pairs(text: str):
    for file_name in _FILE_NAME.finditer(text):
        stem_end = file_name.start() + file_name.group().rfind(".")
        parts = list(_PART.finditer(text, file_name.start(), stem_end))
        for first, second in zip(parts, parts[1:]):
            if text[first.end():second.start()] in _SEPARATORS and not (
                    _technical(first.group()) or _technical(second.group())):
                yield first, second


def _technical(word: str) -> bool:
    return word.lower() in _FILE_WORDS or is_tool_vocabulary(word)


def _is_name(contains, first: str, second: str) -> bool:
    return ((contains("given", first) and contains("family", second))
            or (contains("family", first) and contains("given", second)))
