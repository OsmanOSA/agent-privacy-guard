"""Tokens: the placeholders that replace sensitive values in what the model sees.

Format: ⟦KIND:ID⟧, for example ⟦GITHUB_TOKEN:3FA9C2D1⟧.

- KIND tells the model what the value is, so it can still reason about it.
- ID is an HMAC of the value under a per-session key. The same value always
  gets the same token within a session, and Claude Code's parallel hook
  processes agree on it without sharing any counter.
"""

from __future__ import annotations

import hashlib
import hmac
import re

from privacy_guard.core.findings import Finding

TOKEN_KIND = "token"
TOKEN_ID_LENGTH = 8
TOKEN_PATTERN = re.compile(rf"⟦([A-Z0-9_]+):([0-9A-F]{{{TOKEN_ID_LENGTH}}})⟧")


def token_id(session_key: bytes,
             value: str) -> str:
    """Derives the stable identifier of a value for the current session."""
    digest = hmac.new(session_key, value.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:TOKEN_ID_LENGTH].upper()


def format_token(kind: str,
                 identifier: str) -> str:
    """Builds the placeholder shown to the model."""
    return f"⟦{kind.upper()}:{identifier}⟧"


def find_tokens(text: str) -> list[Finding]:
    """Locates the tokens already present in a text, so they are never tokenized again."""
    return [Finding(TOKEN_KIND, match.start(), match.end()) for match in TOKEN_PATTERN.finditer(text)]
