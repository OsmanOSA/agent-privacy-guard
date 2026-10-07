"""Summaries contain occurrence counts and an optional basename, never values.

Interface: ProtectionSummary(counts, document).message() / record(). Category
names are allowlisted; unknown detector kinds never become log/UI text.
"""

import unicodedata
from pathlib import PureWindowsPath

from privacy_guard.core.category_policy import Mode, mode_for
from privacy_guard.core.secret_detector import SECRET_RULES

_LABELS = {
    "person_name": ("nom", "noms", "m"),
    "email": ("adresse e-mail", "adresses e-mail", "f"),
    "phone": ("numéro de téléphone", "numéros de téléphone", "m"),
    "address": ("adresse postale", "adresses postales", "f"),
    "birth_date": ("date de naissance", "dates de naissance", "f"),
    "banking": ("donnée bancaire", "données bancaires", "f"),
    "identifier": ("identifiant", "identifiants", "m"),
    "secret": ("secret", "secrets", "m"),
    "other": ("donnée sensible", "données sensibles", "f"),
}
_GROUPS = {
    "postal_address": "address", "fr_postal_address": "address",
    "payment_card": "banking", "iban": "banking", "card_security_code": "secret",
    **{rule.kind: "secret" for rule in SECRET_RULES},
    **{kind: "identifier" for kind in ("fr_social_security_number", "fr_tax_number",
       "fr_passport", "fr_license_plate", "fr_siret", "fr_siren", "fr_identity_card", "fr_driving_licence")},
}


class ProtectionSummary:
    def __init__(self, counts: dict[str, int], document: str | None = None):
        self._document = _basename(document)
        self._groups = {"pseudonymized": {}, "redacted": {}}
        for kind, count in counts.items():
            if type(count) is not int or count <= 0:
                raise ValueError("Summary counts must be positive integers")
            category = _GROUPS.get(kind, kind if kind in {"person_name", "email", "phone", "birth_date"} else "other")
            action = "pseudonymized" if mode_for(kind) is Mode.PSEUDONYMIZE else "redacted"
            group = self._groups[action]
            group[category] = group.get(category, 0) + count

    def record(self) -> dict:
        return {"document": self._document, "count_unit": "occurrences_in_tool_result",
                **{action: dict(group) for action, group in self._groups.items()}}

    def message(self) -> str:
        parts = [describe_counts(self._groups[action], verb) for action, verb in (
            ("pseudonymized", "pseudonymisé"), ("redacted", "masqué")) if self._groups[action]]
        source = f" — {self._document}" if self._document else ""
        return f"Privacy Guard{source} : {' ; '.join(parts)}."


def _basename(document: str | None) -> str | None:
    if not isinstance(document, str):
        return None
    name = PureWindowsPath(document).name
    name = "".join(char for char in name if unicodedata.category(char) not in {"Cc", "Cf", "Cs"})
    if name in {"", ".", ".."}:
        return None
    return name if len(name) <= 120 else name[:119] + "…"


def describe_counts(counts: dict, verb: str) -> str:
    """Render allowlisted occurrence categories shared by hook and desktop UI."""
    items, genders = [], []
    for category, (singular, plural, gender) in _LABELS.items():
        if category in counts:
            count = counts[category]
            items.append(f"{count} {singular if count == 1 else plural}")
            genders.append(gender)
    enumeration = items[0] if len(items) == 1 else ", ".join(items[:-1]) + " et " + items[-1]
    ending = ("e" if all(gender == "f" for gender in genders) else "") + ("s" if sum(counts.values()) > 1 else "")
    return f"{enumeration} {verb}{ending}"
