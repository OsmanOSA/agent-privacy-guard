import unittest

from privacy_guard.core.personal_data_detector import find_personal_data


def addresses(text):
    return [text[f.start:f.end] for f in find_personal_data(text) if f.kind == "fr_postal_address"]


class AddressTest(unittest.TestCase):
    def test_detects_full_addresses(self):
        for address in (
            "12 rue de la Paix, 75002 Paris",
            "12 bis avenue Victor Hugo 69003 Lyon",
            "8 rue de l'Église, 13001 Marseille",
            "10 rue du 8 Mai 1945, 75010 Paris",
            "1 place Saint-Germain-des-Prés",
            "3, allée des Tilleuls",
            "27 Boulevard des Capucines 75009 PARIS CEDEX 09",
        ):
            self.assertEqual(addresses(f"Adresse : {address}"), [address], address)

    def test_postal_code_on_the_next_line_belongs_to_the_address(self):
        text = "Jean Dupont\n45 boulevard Haussmann\n75009 Paris\nFrance"

        self.assertEqual(addresses(text), ["45 boulevard Haussmann\n75009 Paris"])

    def test_ordinary_text_is_not_an_address(self):
        for text in (
            "dans la rue il fait beau",
            "il y a 3 rues et 2 avenues",
            "Code postal de livraison : 69003",
            "Commande n° 2026-000451 du 02/10/2026",
            "en 2026 place aux jeunes",
        ):
            self.assertEqual(addresses(text), [], text)


if __name__ == "__main__":
    unittest.main()
