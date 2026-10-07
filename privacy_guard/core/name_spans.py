"""Complete name words and propagate complete spellings within one result.

Interface: complete(text, findings) / spellings(text, findings) /
propagate(text, findings, known). No inference, vault reads or retained values.
Case variants keep their source spelling for exact local restoration.
"""

import re
import unicodedata

from privacy_guard.core.findings import Finding, excluding, without_overlaps
from privacy_guard.core.tokens import find_tokens

_JOINERS = "-'’"
_CLITICS = frozenset({"d", "l", "j", "t", "m", "n", "s", "c", "qu"})


def complete(text: str, findings: list[Finding]) -> list[Finding]:
    result = []
    for finding in findings:
        start, end = finding.start, finding.end
        if not 0 <= start < end <= len(text):
            raise ValueError("Invalid name detection offsets")
        while start > 0 and _word(text[start - 1]):
            start -= 1
        while end < len(text) and _word(text[end]):
            end += 1
        while start > 1 and text[start - 1] in _JOINERS and _word(text[start - 2]):
            previous = start - 2
            while previous > 0 and _word(text[previous - 1]):
                previous -= 1
            if text[start - 1] in "'’" and text[previous:start - 1].lower() in _CLITICS:
                break
            start = previous
        while end + 1 < len(text) and text[end] in _JOINERS and _word(text[end + 1]):
            end += 2
            while end < len(text) and _word(text[end]):
                end += 1
        result.append(Finding(finding.kind, start, end))
    return without_overlaps(result)


def spellings(text: str, findings: list[Finding]) -> set[str]:
    return {text[f.start:f.end] for f in findings if f.kind == "person_name"}


def name_pattern(known: set[str]):
    return re.compile('|'.join(re.escape(name) for name in sorted(known, key=lambda s: (-len(s), s))), re.I)


def propagate(text: str, findings: list[Finding], known: set[str], pattern=None) -> list[Finding]:
    if not known:
        return findings
    # Longest first prevents a shorter known name swallowing a complete one.
    pattern = pattern if pattern is not None else name_pattern(known)
    repeated = []
    for match in pattern.finditer(text):
        start, end = match.span()
        candidate = Finding("person_name", start, end)
        if _whole_spelling(text, start, end):
            repeated.append(candidate)
    reserved = [f for f in findings if f.kind != "person_name"] + find_tokens(text)
    return without_overlaps(findings + excluding(repeated, reserved))


def _word(character: str) -> bool:
    return character.isalnum() or character == "_" or unicodedata.category(character).startswith("M")


def _whole_spelling(text, start, end):
    if (start and _word(text[start - 1])) or (end < len(text) and _word(text[end])):
        return False
    if end + 1 < len(text) and text[end] in _JOINERS and _word(text[end + 1]):
        return False
    if start > 1 and text[start - 1] in _JOINERS and _word(text[start - 2]):
        # A bounded prefix check avoids rescanning long identifiers for every
        # repeated match. Only French clitics may precede an apostrophe.
        prefix = start - 2
        while prefix > 0 and start - 1 - prefix <= 3 and _word(text[prefix - 1]):
            prefix -= 1
        return text[start - 1] in "'’" and text[prefix:start - 1].lower() in _CLITICS
    return True
