"""PrivacyCore: swaps sensitive values for tokens, and tokens back for values.

Interface:
    core = PrivacyCore(vault, names)
    core.protect(text)  -> text where every sensitive span (see core.detector) is a token
    core.restore(text)  -> text where every token of this session is the real value

Both are fast no-ops on the common case where there is nothing to do (PRD §14).
"""

from __future__ import annotations

from privacy_guard.core.detector import SensitiveDataDetector
from privacy_guard.core.name_detector import NameDetector
from privacy_guard.core.tokens import TOKEN_PATTERN, format_token, token_id
from privacy_guard.core.vault import SessionVault

TOKEN_OPENING = "⟦"  # written as an escape so the source never looks like a token


class PrivacyCore:
    """Pseudonymizes and restores text for one agent session."""

    def __init__(self, vault: SessionVault,
                 names: NameDetector) -> None:
        self._vault = vault
        self._detector = SensitiveDataDetector(names)

    def protect(self, text: str) -> str:
        """Replaces every sensitive span with its token."""
        findings = self._detector.find(text)
        if not findings:
            return text

        pieces = []
        cursor = 0
        for finding in findings:
            pieces.append(text[cursor:finding.start])
            pieces.append(self._tokenize(finding.kind, text[finding.start:finding.end]))
            cursor = finding.end
        pieces.append(text[cursor:])

        return "".join(pieces)

    def restore(self, text: str) -> str:
        """Replaces every token issued in this session with its real value.

        Unknown tokens (another session, or invented by the model) stay as they are.
        """
        if TOKEN_OPENING not in text:
            return text
        return TOKEN_PATTERN.sub(self._restore_token, text)

    def _tokenize(self, kind: str,
                  value: str) -> str:
        identifier = token_id(self._vault.session_key(), value)
        self._vault.store(identifier, value)
        return format_token(kind, identifier)

    def _restore_token(self, match) -> str:
        value = self._vault.lookup(match.group(2))
        return match.group(0) if value is None else value
