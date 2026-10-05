"""Finds every sensitive span of a text: secrets, formatted personal data, person names.

Interface: `SensitiveDataDetector(names).find(text) -> list[Finding]`, ordered and non-overlapping.

The single place that decides what is sensitive: PrivacyCore replaces these
spans with tokens, and the quality benchmark (benchmark/) measures them.
"""

from __future__ import annotations

from privacy_guard.core.findings import Finding, excluding, without_overlaps
from privacy_guard.core.name_detector import NameDetector
from privacy_guard.core.personal_data_detector import find_personal_data
from privacy_guard.core.secret_detector import find_secrets
from privacy_guard.core.tabular import find_tabular_personal_data
from privacy_guard.core.tokens import find_tokens


class SensitiveDataDetector:
    """Combines every detector, with a fixed priority when they disagree."""

    def __init__(self, names: NameDetector) -> None:
        self._names = names

    def find(self, text: str) -> list[Finding]:
        # Priority: secrets, then formatted personal data, then names. In
        # postgres://admin:pass@db.example.com, "pass@db.example.com" looks like an
        # email but only the password is sensitive.
        secrets = find_secrets(text)
        formatted = without_overlaps(find_personal_data(text) + find_tabular_personal_data(text))
        personal_data = excluding(formatted, secrets)
        names = excluding(self._find_names(text), secrets + personal_data)
        findings = sorted(secrets + personal_data + names, key=lambda finding: finding.start)

        # Tokens already in the text are never tokenized again.
        return excluding(findings, find_tokens(text))

    def _find_names(self, text: str) -> list[Finding]:
        # A name starts with a capital letter: text without one (most tool output
        # fields, numbers, paths) skips the round trip to the name service.
        if not any(character.isupper() for character in text):
            return []
        return self._names.find_names(text)
