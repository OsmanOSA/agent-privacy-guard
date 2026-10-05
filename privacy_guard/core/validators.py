"""Validators that tell a real identifier from a look-alike number.

Each function takes the value as written (spaces and dashes allowed) and
returns whether its official control key, or structure, is right.
"""

from __future__ import annotations

import re

# Payment card networks: (first digits, allowed lengths).
_CARD_NETWORKS = (
    (("4",), (13, 16, 19)),                                      # Visa
    (tuple(str(n) for n in range(51, 56)), (16,)),               # Mastercard
    (tuple(str(n) for n in range(2221, 2721)), (16,)),           # Mastercard 2-series
    (("34", "37"), (15,)),                                       # American Express
    (("6011", "65") + tuple(str(n) for n in range(644, 650)), (16, 17, 18, 19)),  # Discover
    (("36", "38") + tuple(str(n) for n in range(300, 306)), (14, 15, 16, 17, 18, 19)),  # Diners
    (tuple(str(n) for n in range(3528, 3590)), (16, 17, 18, 19)),  # JCB
)


def payment_card_valid(value: str) -> bool:
    """Known card network prefix and length, plus a valid Luhn checksum."""
    digits = _compact(value)
    known_network = any(
        digits.startswith(prefixes) and len(digits) in lengths for prefixes, lengths in _CARD_NETWORKS
    )
    return known_network and luhn_valid(digits)


def luhn_valid(value: str) -> bool:
    """Luhn checksum, used by payment cards."""
    total = 0
    for position, character in enumerate(reversed(_compact(value))):
        digit = int(character)
        if position % 2:
            digit = digit * 2 - 9 if digit > 4 else digit * 2
        total += digit
    return total % 10 == 0


def iban_valid(value: str) -> bool:
    """ISO 13616 check: the rearranged IBAN, read as a number, modulo 97 equals 1."""
    iban = _compact(value).upper()
    rearranged = iban[4:] + iban[:4]
    # Letters count as two-digit numbers: A=10 ... Z=35.
    return int("".join(str(int(character, 36)) for character in rearranged)) % 97 == 1


def nir_valid(value: str) -> bool:
    """French social security number: key = 97 - (13 first characters mod 97).

    Corsica departments 2A and 2B are computed as 19 and 18.
    """
    nir = _compact(value).upper()
    body = nir[:13].replace("2A", "19").replace("2B", "18")
    return body.isdigit() and 97 - int(body) % 97 == int(nir[13:])


def fr_tax_number_valid(value: str) -> bool:
    """French tax number (numéro fiscal): the 3 last digits are the 10 first modulo 511."""
    number = _compact(value)
    return int(number[:10]) % 511 == int(number[10:])


def _compact(value: str) -> str:
    return re.sub(r"[\s.-]", "", value)
