"""French personal data with an official format.

Identifiers with a control key are only reported when the key is right, which
rules out almost every look-alike number (1 chance in 97 for a NIR, 1 in 511
for a tax number). Identifiers without a key rely on a distinctive format.
"""

from __future__ import annotations

from privacy_guard.core.french_address import FRENCH_ADDRESS_RULE
from privacy_guard.core.pattern_rule import NUMBER_END, NUMBER_START, rule
from privacy_guard.core.validators import fr_tax_number_valid, iban_valid, nir_valid

# Letters used on French plates (SIV): I, O and U are excluded.
_PLATE_LETTERS = "[A-HJ-NP-TV-Z]"

FRENCH_RULES = (
    # Numéro de sécurité sociale (NIR): sex, birth year and month, department
    # (2A/2B for Corsica), commune, order, key. Spaces allowed between groups.
    rule(
        "fr_social_security_number",
        NUMBER_START + r"[1-478](?: ?\d){4} ?(?:\d{2}|2[AB])(?: ?\d){8}" + NUMBER_END,
        nir_valid,
    ),
    # Numéro fiscal: 13 digits starting with 0 to 3.
    rule("fr_tax_number", NUMBER_START + r"[0-3](?: ?\d){12}" + NUMBER_END, fr_tax_number_valid),
    # French and Monegasque IBAN: 27 characters, usually in groups of 4.
    rule("iban", r"\b(?:FR|MC)\d{2}(?: ?[A-Z0-9]{4}){5} ?[A-Z0-9]{3}\b", iban_valid),
    # Passport: 2 digits, 2 letters, 5 digits (e.g. 12AB34567).
    rule("fr_passport", r"\b\d{2}[A-Z]{2}\d{5}\b"),
    # License plate (SIV, since 2009): AB-123-CD.
    rule("fr_license_plate", rf"\b{_PLATE_LETTERS}{{2}}[- ]\d{{3}}[- ]{_PLATE_LETTERS}{{2}}\b"),
    # Phone, national format: 06 12 34 56 78, 06.12.34.56.78, 0612345678.
    rule("phone", NUMBER_START + r"0[1-9](?:[ .-]?\d{2}){4}" + NUMBER_END),
    FRENCH_ADDRESS_RULE,
)
