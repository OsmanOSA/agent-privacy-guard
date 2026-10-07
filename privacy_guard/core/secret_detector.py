"""Detection of secrets with a known format (PRD §8.3, fast scanner).

Interface: `find_secrets(text) -> list[Finding]`, ordered and non-overlapping.

Regex only: this runs on every file the agent reads, so it has to stay fast.
Rules are listed from the most specific to the most generic, which decides the
reported kind when two rules match the same value.
"""

from __future__ import annotations

from privacy_guard.core.findings import Finding
from privacy_guard.core.pattern_rule import find_with, rule


def _looks_like_secret(value: str) -> bool:
    # Secrets carry digits or are long; a short word is a setting such as
    # API_KEY_HEADER = "X-Api-Key".
    return any(character.isdigit() for character in value) or len(value) >= 16


SECRET_RULES = (
    rule("private_key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    # Only the password: the model can still see the scheme, user and host to help debug.
    rule("url_password", r"\b[a-z][a-z0-9+.-]*://[^:/\s@]*:(?P<value>[^@/\s]+)@"),
    # Secret (sk_) and restricted (rk_) keys. Publishable keys (pk_) are public by design.
    rule("stripe_secret_key", r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}"),
    rule("anthropic_api_key", r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    rule("openai_api_key", r"\bsk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{20,}"),
    rule("aws_access_key_id", r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    rule("github_token", r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})"),
    rule("jwt", r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    # A key that announces a secret, in any casing and place: JWT_SECRET=..., password: ...
    # in YAML, "api_key": "..." in JSON, user=x password=... in a log, mot de passe : ...
    # The value must be a whole literal of 8+ characters without code punctuation
    # (API_KEY = os.environ["X"] is code), and look like a secret (_looks_like_secret).
    # [ \t] rather than \s: an empty value must not swallow the next line.
    # Token metrics/tokenizer settings and self-references are not credential
    # literals; retain access_token, authToken and actual quoted secret values.
    rule(
        "secret_assignment",
        r"(?<![\w.])[\"']?(?P<label>(?i:[a-z0-9_.-]*(?:secret|password|passwd|token(?![a-z])|api[_-]?key|private[_-]?key)"
        r"[a-z0-9_-]*|mot de passe|mdp))[\"']?[ \t]*[=:][ \t]*[\"']?"
        r"(?!(?P=label)(?=[\"'\s#,;)]|$))"
        r"(?P<value>[^\s\"'#()\[\]{}$<>,;]{8,})(?=[\"'\s#,;]|$)",
        _looks_like_secret,
    ),
)


def find_secrets(text: str) -> list[Finding]:
    """Returns the secrets found in the text, ordered by position, without overlaps."""
    return find_with(SECRET_RULES, text)
