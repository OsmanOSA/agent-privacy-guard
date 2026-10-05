"""French personal data that is only recognisable by its label.

A 9-digit SIREN or a 3-digit card code looks like any other number: on its own
it cannot be told apart without flooding the agent with false positives. Next
to its label ("SIRET :", "N° CNI", "Cryptogramme"), it can.
"""

from __future__ import annotations

from privacy_guard.core.pattern_rule import labelled_rule
from privacy_guard.core.validators import luhn_valid

_APOSTROPHE = "['’]"
# Document numbers contain at least one digit: "Pièce d'identité : PASSEPORT" names a document, not a number.
_HAS_DIGIT = r"(?=[A-Z]*\d)"
_FRENCH_MONTHS = (
    "janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre"
)

FRENCH_CONTEXT_RULES = (
    # Company identifiers carry a Luhn key: a wrong key means it is not one.
    labelled_rule("fr_siret", "siret", r"\d{3} ?\d{3} ?\d{3} ?\d{5}", luhn_valid),
    labelled_rule("fr_siren", "siren", r"\d{3} ?\d{3} ?\d{3}", luhn_valid),
    # Identity card: 12 characters (before 2021) or 9 (since 2021).
    labelled_rule(
        "fr_identity_card",
        rf"cni|carte (?:nationale )?d{_APOSTROPHE}identit[ée]|pi[eè]ce d{_APOSTROPHE}identit[ée]",
        _HAS_DIGIT + r"(?:[A-Z0-9]{12}|[A-Z0-9]{9})",
    ),
    # Driving licence number. At least 9 characters, so "Permis : B" (a category) is not one.
    labelled_rule("fr_driving_licence", "permis(?: de conduire)?", _HAS_DIGIT + r"[A-Z0-9]{9,12}"),
    labelled_rule(
        "card_security_code",
        "cvv2?|cvc2?|cryptogramme(?: visuel)?|code de s[ée]curit[ée]",
        r"\d{3,4}",
    ),
    labelled_rule(
        "birth_date",
        r"date de naissance|n[ée]e? le|date of birth|dob",
        rf"\d{{1,2}}[/.-]\d{{1,2}}[/.-]\d{{2,4}}|\d{{1,2}}(?:er)? (?:{_FRENCH_MONTHS}) \d{{4}}",
    ),
)
