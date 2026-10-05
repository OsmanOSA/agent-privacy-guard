import unittest
from pathlib import Path

from privacy_guard.core.personal_data_detector import find_personal_data

FICHE_CLIENT = Path(__file__).resolve().parent.parent / "playground" / "fiche_client.txt"

# Everything playground/fiche_client.txt must hide today (names need NLP, later).
FICHE_CLIENT_FINDINGS = {
    ("fr_postal_address", "12 rue de la Paix, 75002 Paris"),
    ("phone", "06 12 34 56 78"),
    ("email", "jean.dupont@example.com"),
    ("fr_social_security_number", "1 85 05 78 006 084 91"),
    ("fr_tax_number", "1234567890066"),
    ("fr_passport", "12AB34567"),
    ("fr_license_plate", "AB-123-CD"),
    ("iban", "FR76 3000 6000 0112 3456 7890 189"),
    ("payment_card", "4111 1111 1111 1111"),
    ("card_security_code", "737"),
    ("birth_date", "15/03/1985"),
    ("fr_identity_card", "X4RTBPFW4"),
    ("fr_driving_licence", "123456789012"),
    ("fr_siret", "123 456 782 00010"),
    ("fr_siren", "123456782"),
}


def detected(text):
    return {(finding.kind, text[finding.start:finding.end]) for finding in find_personal_data(text)}


class FicheClientTest(unittest.TestCase):
    def test_detects_every_identifier_and_nothing_else(self):
        self.assertEqual(detected(FICHE_CLIENT.read_text(encoding="utf-8")), FICHE_CLIENT_FINDINGS)


class SocialSecurityNumberTest(unittest.TestCase):
    def test_accepts_valid_keys_in_every_layout(self):
        for nir in ("1 85 05 78 006 084 91", "185057800608491", "2 93 02 75 123 456 68", "1 85 05 2A 004 012 70"):
            self.assertEqual(detected(f"NIR {nir}"), {("fr_social_security_number", nir)}, nir)

    def test_rejects_a_wrong_key(self):
        self.assertEqual(detected("NIR 1 85 05 78 006 084 92"), set())


class BankingTest(unittest.TestCase):
    def test_accepts_valid_ibans(self):
        for iban in ("FR76 3000 6000 0112 3456 7890 189", "FR7630006000011234567890189", "FR14 2004 1010 0505 0001 3M02 606"):
            self.assertEqual(detected(f"IBAN {iban}"), {("iban", iban)}, iban)

    def test_rejects_an_iban_with_a_wrong_key(self):
        self.assertEqual(detected("IBAN FR77 3000 6000 0112 3456 7890 189"), set())

    def test_accepts_cards_of_the_main_networks(self):
        for card in ("4111 1111 1111 1111", "5555-5555-5555-4444", "378282246310005"):
            self.assertEqual(detected(f"card {card}"), {("payment_card", card)}, card)

    def test_decimals_are_not_card_numbers(self):
        # 5555555555554444 is a valid Mastercard test number, but here it is the fraction of a score.
        self.assertEqual(detected("'confidence': 0.5555555555554444, 'start': 3"), set())

    def test_rejects_cards_failing_luhn_or_with_unknown_network(self):
        for number in ("4111 1111 1111 1112", "9111 1111 1111 1111"):
            self.assertEqual(detected(f"card {number}"), set(), number)


class OtherIdentifiersTest(unittest.TestCase):
    def test_tax_number_needs_a_valid_key(self):
        self.assertEqual(detected("fiscal 0312345678505"), {("fr_tax_number", "0312345678505")})
        self.assertEqual(detected("fiscal 0312345678506"), set())

    def test_license_plate_excludes_letters_never_issued(self):
        self.assertEqual(detected("AB-123-CD et AB 123 CD"), {("fr_license_plate", "AB-123-CD"), ("fr_license_plate", "AB 123 CD")})
        self.assertEqual(detected("IO-123-UO"), set())


if __name__ == "__main__":
    unittest.main()
