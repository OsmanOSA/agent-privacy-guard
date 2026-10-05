"""Person names recognised from their context: a label ("Nom :"), a title ("Madame"),
or a mailbox ("Jean Dupont <jean@example.com>").

Interface: `HeuristicNameDetector().find_names(text) -> list[Finding]`.

Instant, but it only sees names announced by their context. It covers every
tool output; documents also go through the NER model of the background service
(see service/onnx_name_detector.py), combined with this one.
"""

from __future__ import annotations

from typing import Protocol

from privacy_guard.core.findings import Finding, without_overlaps
from privacy_guard.core.pattern_rule import find_with, rule

PERSON_NAME = "person_name"


class NameDetector(Protocol):
    """Finds person names: the heuristic below, or the NER model of the background service."""

    def find_names(self, text: str) -> list[Finding]: ...


# A name word starts with a capital: "Jean", "DUPONT", "Saint-Éloi", "O'Brien".
_NAME_WORD = r"[A-ZÀ-ÖØ-Ý][\w'’-]*"
_NAME_PARTICLE = r"(?:de|du|des|van|von|der|le|la|ben|el|al)"
_FULL_NAME = rf"{_NAME_WORD}(?:[ \t]+(?:{_NAME_PARTICLE}[ \t]+)*{_NAME_WORD}){{0,3}}"
_FIRST_AND_LAST_NAME = rf"{_NAME_WORD}(?:[ \t]+(?:{_NAME_PARTICLE}[ \t]+)*{_NAME_WORD}){{1,3}}"

_LABELS = (
    r"nom(?: complet| de naissance| d['’]usage| de famille)?|pr[ée]noms?|auteur|"
    r"full[ _]name|first[ _]name|last[ _]name|surname|name|author|maintainer|contact|"
    r"assignee|owner|reporter|signed-off-by|co-authored-by|reviewed-by"
)
# The label, possibly quoted as a JSON or dictionary key: "name": "Jean Dupont".
_LABEL = rf"(?i:\b(?:{_LABELS}))[\"']?"
# Phrases that introduce a person without a colon: "reported by Lucas Morel".
_BY_PHRASES = (
    r"reported by|written by|authored by|maintained by|requested by|reviewed by|"
    r"r[ée]dig[ée] par|sign[ée] par|demand[ée] par"
)
# Titles are case-sensitive: "M." is a title, "m." is not.
_TITLES = (
    r"M\.|MM\.|Mme|Mmes|Mlle|Monsieur|Madame|Mademoiselle|Docteur|Ma[iî]tre|"
    r"Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Pr\."
)
# "name: String" is a typed field in code, not a person.
_TYPE_NAMES = frozenset(
    {"String", "Str", "Text", "Integer", "Int", "Boolean", "Bool", "Optional", "List",
     "None", "Null", "Any", "Object", "Number", "Date", "Field", "Column", "Char", "Varchar"}
)


def _is_not_a_type(value: str) -> bool:
    return value.split()[0].rstrip("!?") not in _TYPE_NAMES


NAME_RULES = (
    rule(PERSON_NAME, rf"{_LABEL}[ \t]*:[ \t]*[\"']?(?P<value>{_FULL_NAME})", _is_not_a_type),
    # name="Alice Martin": a keyword argument or an attribute. Two words at least:
    # a single capitalised word there is usually code (name="Default").
    rule(PERSON_NAME, rf"{_LABEL}[ \t]*=[ \t]*[\"']?(?P<value>{_FIRST_AND_LAST_NAME})", _is_not_a_type),
    rule(PERSON_NAME, rf"\b(?:{_TITLES})[ \t]+(?P<value>{_FULL_NAME})"),
    rule(PERSON_NAME, rf"(?i:\b(?:{_BY_PHRASES}))[ \t]+(?P<value>{_FULL_NAME})"),
    # TODO(Camille Fontaine): a code comment assigned to a person.
    rule(PERSON_NAME, rf"\b(?:TODO|FIXME|XXX)\((?P<value>{_FULL_NAME})\)"),
    # "Jean Dupont <jean@example.com>": the mailbox format of git, npm, email headers
    # and code authorship. A capitalised name right before an address in angle brackets.
    rule(PERSON_NAME, rf"\b(?P<value>{_FULL_NAME})[ \t]*<[^<>\s@]+@[^<>\s]+>"),
)


class HeuristicNameDetector:
    """Finds the names announced by a label, a title, or an email address in angle brackets."""

    def find_names(self, text: str) -> list[Finding]:
        return find_with(NAME_RULES, text)


class PlausibleNameFilter:
    """Drops what a NER model reports as a person but cannot be a name in a document.

    Seen on developer documents: "fastino" in a URL, a user name in an `ls`
    listing, "GLiNER2", "ONNX". A person name starts with a capital, has no digit,
    is not glued to a path or URL character, and is not a short all-caps acronym.
    Company names that look like first names ("Fastino") remain a known limit.
    """

    _IDENTIFIER_NEIGHBOURS = frozenset("/\\@_=")
    _MAX_ACRONYM_LENGTH = 4

    def __init__(self, detector) -> None:
        self._detector = detector

    def find_names(self, text: str) -> list[Finding]:
        return [finding for finding in self._detector.find_names(text) if self._is_plausible(text, finding)]

    def _is_plausible(self, text: str,
                      finding: Finding) -> bool:
        name = text[finding.start:finding.end]
        before = text[finding.start - 1] if finding.start > 0 else " "
        after = text[finding.end] if finding.end < len(text) else " "
        return (
            name[:1].isupper()
            and not any(character.isdigit() for character in name)
            and before not in self._IDENTIFIER_NEIGHBOURS
            and after not in self._IDENTIFIER_NEIGHBOURS
            and not (name.isupper() and " " not in name and len(name) <= self._MAX_ACRONYM_LENGTH)
        )


class CombinedNameDetector:
    """Merges several detectors: a name found by any of them is reported once."""

    def __init__(self, detectors: list) -> None:
        self._detectors = detectors

    def find_names(self, text: str) -> list[Finding]:
        return without_overlaps(finding for detector in self._detectors for finding in detector.find_names(text))
