import unittest

from privacy_guard.core.personal_data_detector import find_personal_data


def detected(text):
    return {(finding.kind, text[finding.start:finding.end]) for finding in find_personal_data(text)}


class LabelTest(unittest.TestCase):
    def test_label_variants_are_recognised(self):
        for text in ("SIRET : 12345678200010", "N° SIRET 12345678200010", "siret n° 12345678200010", "Siret: 12345678200010"):
            self.assertEqual(detected(text), {("fr_siret", "12345678200010")}, text)

    def test_value_without_its_label_is_left_alone(self):
        self.assertEqual(detected("Total 12345678200010 et code 737"), set())


class CompanyIdentifierTest(unittest.TestCase):
    def test_siren_and_siret_need_a_valid_luhn_key(self):
        self.assertEqual(detected("SIREN 123 456 782"), {("fr_siren", "123 456 782")})
        self.assertEqual(detected("SIREN 123 456 783"), set())
        self.assertEqual(detected("SIRET 98765432400027"), {("fr_siret", "98765432400027")})


class IdentityDocumentTest(unittest.TestCase):
    def test_identity_card_old_and_new_formats(self):
        self.assertEqual(detected("Carte d'identité n° 880692310285"), {("fr_identity_card", "880692310285")})
        self.assertEqual(detected("CNI : X4RTBPFW4"), {("fr_identity_card", "X4RTBPFW4")})

    def test_document_names_are_not_numbers(self):
        self.assertEqual(detected("Pièce d’identité : PASSEPORT"), set())
        self.assertEqual(detected("Permis : B"), set())


class CardSecurityCodeTest(unittest.TestCase):
    def test_detects_labelled_codes(self):
        for text in ("CVV: 123", "Cryptogramme visuel : 4321", "code de sécurité 999"):
            self.assertEqual(len(detected(text)), 1, text)


class BirthDateTest(unittest.TestCase):
    def test_detects_numeric_and_written_dates(self):
        self.assertEqual(detected("Date de naissance : 15/03/1985"), {("birth_date", "15/03/1985")})
        self.assertEqual(detected("née le 1er février 1990"), {("birth_date", "1er février 1990")})

    def test_other_dates_are_not_personal(self):
        self.assertEqual(detected("Commande du 02/10/2026, livrée le 05/10/2026"), set())
        self.assertEqual(detected("Année le 02/10/2026"), set())


if __name__ == "__main__":
    unittest.main()
