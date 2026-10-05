import unittest
from pathlib import Path

from privacy_guard.core.personal_data_detector import find_personal_data

PLAYGROUND_ENV = Path(__file__).resolve().parent.parent / "playground" / ".env"


def detected(text):
    return {(finding.kind, text[finding.start:finding.end]) for finding in find_personal_data(text)}


class PlaygroundEnvTest(unittest.TestCase):
    def test_detects_the_email_and_the_phone(self):
        env = PLAYGROUND_ENV.read_text(encoding="utf-8")

        found = detected(env)

        self.assertIn(("email", "jean.dupont@example.com"), found)
        self.assertIn(("phone", "+33 6 12 34 56 78"), found)


class EmailTest(unittest.TestCase):
    def test_detects_common_emails(self):
        for email in ("jean.dupont@example.com", "j+tag@mail.example.co.uk", "first_last@sub.domain.fr"):
            self.assertEqual(detected(f"contact: {email}."), {("email", email)}, email)

    def test_ignores_addresses_without_a_domain_suffix(self):
        self.assertEqual(detected("user@localhost and pkg@1.2.3"), set())


class PhoneTest(unittest.TestCase):
    def test_detects_french_and_international_formats(self):
        for phone in (
            "06 12 34 56 78",
            "06.12.34.56.78",
            "0612345678",
            "+33 6 12 34 56 78",
            "+33612345678",
            "+1 415 555 0132",
            "(415) 555-0132",
            "415-555-0132",
        ):
            self.assertEqual(detected(f"call {phone} now"), {("phone", phone)}, phone)

    def test_ignores_numbers_that_are_not_phones(self):
        for text in ("20261002191407", "port 3000", "version 1.2.3", "id 4155550132", "192.168.1.10"):
            self.assertEqual(detected(text), set(), text)


if __name__ == "__main__":
    unittest.main()
