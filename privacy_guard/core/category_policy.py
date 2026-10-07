"""Choose reversible pseudonymization or irreversible redaction for a finding.

Interface: mode_for(kind) -> Mode. Detection and destination authorization remain
separate. Unknown kinds redact; no runtime overrides can disable protection.

Adapted from AgenticRAG src/security/pii_rules.py, copyright (c) 2026
Osman Said Ali. MIT notice: licenses/AgenticRAG-MIT.txt.
"""

from enum import Enum

from privacy_guard.core.secret_detector import SECRET_RULES


class Mode(Enum):
    REDACT = "redact"
    PSEUDONYMIZE = "pseudonymize"


# The detector's secret kinds cannot become reversible through an allow-list edit.
_REDACT_ONLY = frozenset(rule.kind for rule in SECRET_RULES) | {"card_security_code"}

# Preserve the existing personal-data round trip in this first adaptation.
# Financial and identity categories can be restricted in a separate policy change.
_PSEUDONYMIZE = frozenset({
    "person_name", "email", "phone", "postal_address", "fr_postal_address",
    "birth_date", "payment_card", "iban", "fr_social_security_number",
    "fr_tax_number", "fr_passport", "fr_license_plate", "fr_siret", "fr_siren",
    "fr_identity_card", "fr_driving_licence",
})


def mode_for(kind: str) -> Mode:
    """Secrets and unknown kinds redact; approved personal kinds use session tokens."""
    if kind in _REDACT_ONLY:
        return Mode.REDACT
    return Mode.PSEUDONYMIZE if kind in _PSEUDONYMIZE else Mode.REDACT
