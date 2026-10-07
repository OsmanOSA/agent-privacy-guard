import unittest

from privacy_guard.service.ner_unicode import must_be_covered, tokenizable


class TokenizableTest(unittest.TestCase):
    def test_lone_surrogates_become_spaces_without_moving_offsets(self):
        # How an undecodable cp1252 byte arrives after surrogateescape decoding.
        text = b"Caf\xe8 Camille".decode("utf-8", errors="surrogateescape")
        cleaned = tokenizable(text)
        self.assertEqual(cleaned, "Caf  Camille")
        self.assertEqual(len(cleaned), len(text))
        self.assertEqual(cleaned.index("Camille"), text.index("Camille"))

    def test_valid_text_is_unchanged(self):
        text = "Hélène Dupont-Lefèvre, 06 41 27 85 93 � \x07"
        self.assertEqual(tokenizable(text), text)


class MustBeCoveredTest(unittest.TestCase):
    def test_characters_that_can_belong_to_a_name(self):
        for char in ("a", "É", "ß", "́", "7", "李"):
            with self.subTest(char=char):
                self.assertTrue(must_be_covered(char))

    def test_separators_symbols_and_controls_may_be_skipped(self):
        for char in (" ", "\n", ",", "-", "�", "\x07", "​", "€", "\udce8"):
            with self.subTest(char=repr(char)):
                self.assertFalse(must_be_covered(char))


if __name__ == "__main__":
    unittest.main()
