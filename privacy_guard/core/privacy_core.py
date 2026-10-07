"""PrivacyCore: redacts secrets and reversibly pseudonymizes personal data.

Interface:
    core = PrivacyCore(vault, names)
    core.protect(text)  -> text with category redactions or session tokens
    core.restore(text)  -> text with this session's approved personal values restored

Both are fast no-ops on the common case where there is nothing to do (PRD §14).
"""

from __future__ import annotations

from collections import Counter

from privacy_guard.core.bound_values import BoundValues
from privacy_guard.core.category_policy import Mode, mode_for
from privacy_guard.core.detector import SensitiveDataDetector
from privacy_guard.core.name_detector import NameDetector
from privacy_guard.core.tokens import TOKEN_PATTERN, format_redaction, format_token, token_id
from privacy_guard.core.vault import SessionVault
from privacy_guard.diagnostics import stage

TOKEN_OPENING = "⟦"  # written as an escape so the source never looks like a token


class PrivacyCore:
    """Pseudonymizes and restores text for one agent session."""

    def __init__(self, vault: SessionVault,
                 names: NameDetector) -> None:
        self._vault = vault
        self._values = BoundValues(vault)
        self._detector = SensitiveDataDetector(names)

    def protect(self, text: str) -> str:
        """Redacts secrets; stores reversible personal values in the encrypted vault."""
        return self.protect_with_counts(text)[0]

    def protect_with_counts(self, text: str) -> tuple[str, dict[str, int]]:
        """Return committed protection and counts from the same detection pass."""
        return self.protect_many_with_counts([text])[0]

    def protect_many_with_counts(self, texts: list[str]) -> list[tuple[str, dict[str, int]]]:
        """Inspect once per string; reuse this session's committed complete names."""
        if not texts:
            return []
        with stage('session_names'):
            known = self._values.known_names()
        # Release storage access before potentially slow document inference.
        with stage('detection'):
            detected = self._detector.find_many(texts, known)
        with stage('vault_commit'):
            with self._vault.batch():
                with stage('vault_write'):
                    prepared = [self._protect_findings(text, found) for text, found in zip(texts, detected)]
            return prepared

    def _protect_findings(self, text, findings) -> tuple[str, dict[str, int]]:
        if not findings:
            return text, {}

        pieces = []
        cursor = 0
        with self._vault.batch():
            for finding in findings:
                pieces.append(text[cursor:finding.start])
                pieces.append(self._tokenize(finding.kind, text[finding.start:finding.end]))
                cursor = finding.end
        pieces.append(text[cursor:])

        return "".join(pieces), dict(Counter(finding.kind for finding in findings))

    def restore(self, text: str) -> str:
        """Restores approved personal tokens from this session.

        Redactions, secret-kind tokens and unknown tokens stay as they are.
        The caller still needs to authorize the operation and destination.
        """
        if TOKEN_OPENING not in text:
            return text
        with stage('restoration'):
            with self._vault.batch():
                return TOKEN_PATTERN.sub(self._restore_token, text)

    def _tokenize(self, kind: str,
                  value: str) -> str:
        if mode_for(kind) is Mode.REDACT:
            return format_redaction(kind)
        identifier = token_id(self._vault.session_key(), value)
        self._values.store(kind, identifier, value)
        return format_token(kind, identifier)

    def _restore_token(self, match) -> str:
        if mode_for(match.group(1).lower()) is Mode.REDACT:
            return match.group(0)
        value = self._values.lookup(match.group(1).lower(), match.group(2))
        return match.group(0) if value is None else value
