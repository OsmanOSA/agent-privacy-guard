"""Detection of personal data with a recognisable format.

Interface: `find_personal_data(text) -> list[Finding]`, ordered and non-overlapping.

Regex and checksums only, like the secret detector. Country-specific rules live
in their own module (French first, PRD §23); this module holds the formats
shared across countries. Names and postal addresses need context and a local
NLP model (PRD §8.4): they are out of this module's reach.
"""

from __future__ import annotations

from privacy_guard.core.findings import Finding
from privacy_guard.core.french_context_rules import FRENCH_CONTEXT_RULES
from privacy_guard.core.french_rules import FRENCH_RULES
from privacy_guard.core.pattern_rule import NUMBER_END, NUMBER_START, find_with, rule
from privacy_guard.core.validators import payment_card_valid

INTERNATIONAL_RULES = (
    rule("email", r"(?<![\w.%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b"),
    # Card number, 13 to 19 digits, grouped or not: network prefix + Luhn required.
    rule("payment_card", NUMBER_START + r"\d(?:[ -]?\d){12,18}" + NUMBER_END, payment_card_valid),
    # International phone with a leading +: +33 6 12 34 56 78, +1 415 555 0132.
    rule("phone", NUMBER_START + r"\+\d{1,3}(?:[ .-]?\d){6,14}" + NUMBER_END),
    # North American phone. Separators are required: ten bare digits are far
    # more often an identifier.
    rule("phone", NUMBER_START + r"(?:\(\d{3}\) ?|\d{3}[ .-])\d{3}[ .-]\d{4}" + NUMBER_END),
)

# Most specific first, since the first rule wins a tie: labelled values, then
# country formats, then international formats.
PERSONAL_DATA_RULES = FRENCH_CONTEXT_RULES + FRENCH_RULES + INTERNATIONAL_RULES


def find_personal_data(text: str) -> list[Finding]:
    """Returns the personal data found in the text, ordered by position."""
    return [finding for finding in find_with(PERSONAL_DATA_RULES, text)
            if not _diff_decorator(text, finding)]


def _diff_decorator(text: str, finding: Finding) -> bool:
    if finding.kind != "email" or text[finding.end:finding.end + 1] != "(":
        return False
    local = text[finding.start:finding.end].split("@", 1)[0]
    line_start = text.rfind("\n", 0, finding.start) + 1
    # +@app.post(...) is an added decorator, not a mailbox whose local part
    # is '+'. Retain unusual real mailboxes in other contexts.
    return local in {"+", "-"} and not text[line_start:finding.start].strip()
