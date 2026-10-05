import unittest

from benchmark.annotation import Expected, parse
from benchmark.scoring import Report
from privacy_guard.core.findings import Finding


class AnnotationTest(unittest.TestCase):
    def test_strips_markup_and_locates_values(self):
        document = parse("doc.txt", "Bonjour ⟪name:Jean Dupont⟫, écrivez à ⟪email:jd@example.com⟫.")

        self.assertEqual(document.text, "Bonjour Jean Dupont, écrivez à jd@example.com.")
        self.assertEqual(document.expected, (Expected("name", 8, 19), Expected("email", 31, 45)))

    def test_rejects_unknown_categories(self):
        with self.assertRaises(ValueError):
            parse("doc.txt", "⟪colour:blue⟫")


class ScoringTest(unittest.TestCase):
    def setUp(self):
        self.document = parse("doc.txt", "⟪name:Jean Dupont⟫, ⟪email:jd@example.com⟫, Acme")
        self.report = Report()

    def test_overlapping_finding_of_the_same_category_hides_the_value(self):
        self.report.add(self.document, [Finding("person_name", 0, 4), Finding("email", 13, 27)])

        self.assertEqual(self.report.scores["name"].recall, 1.0)
        self.assertEqual(self.report.missed, [])

    def test_counts_leaks_and_noise(self):
        self.report.add(self.document, [Finding("person_name", 29, 33)])

        self.assertEqual(self.report.scores["name"].precision, 0.0)
        self.assertEqual([m.value for m in self.report.missed], ["Jean Dupont", "jd@example.com"])
        self.assertEqual([m.value for m in self.report.false_alarms], ["Acme"])


if __name__ == "__main__":
    unittest.main()
