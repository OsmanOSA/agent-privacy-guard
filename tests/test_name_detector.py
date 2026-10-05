import unittest

from privacy_guard.core.findings import Finding
from privacy_guard.core.name_detector import HeuristicNameDetector, PlausibleNameFilter


def names(text):
    return [text[f.start:f.end] for f in HeuristicNameDetector().find_names(text)]


class LabelledNameTest(unittest.TestCase):
    def test_detects_names_after_a_label(self):
        for text, expected in (
            ("Nom : Jean Dupont", "Jean Dupont"),
            ("Prénom: Marie", "Marie"),
            ("NOM DE FAMILLE : DUPONT", "DUPONT"),
            ("Full name: Anne-Sophie van der Berg", "Anne-Sophie van der Berg"),
        ):
            self.assertEqual(names(text), [expected], text)

    def test_ignores_typed_fields_in_code(self):
        for text in ("name: String!", "name: Optional[str]", "name: str", "Nom de l'entreprise : Acme"):
            self.assertEqual(names(text), [], text)


class TitledNameTest(unittest.TestCase):
    def test_detects_names_after_a_title(self):
        for text, expected in (
            ("Bonjour Madame Marie Martin,", "Marie Martin"),
            ("M. Dupont a signé", "Dupont"),
            ("Dr. Emily Stone", "Emily Stone"),
            ("Mrs. Smith", "Smith"),
        ):
            self.assertEqual(names(text), [expected], text)

    def test_titles_are_case_sensitive(self):
        self.assertEqual(names("m. le maire et le docteur"), [])


class ContextualNameTest(unittest.TestCase):
    def test_detects_names_in_developer_formats(self):
        for text, expected in (
            ("Author: Camille Fontaine <camille@example.org>", "Camille Fontaine"),
            ('"author": "Rahul Mehta <rahul@example.net>"', "Rahul Mehta"),
            ("Fix retry (reported by Lucas Morel)", "Lucas Morel"),
            ("# TODO(Camille Fontaine): move to settings", "Camille Fontaine"),
            ('User(name="Alice Martin", email=x)', "Alice Martin"),
            ('{"name": "Alice Martin"}', "Alice Martin"),
            ("Signed-off-by: Inès Barbier", "Inès Barbier"),
        ):
            self.assertEqual(names(text), [expected], text)

    def test_ignores_code_and_bots(self):
        for text in ('name="Default"', "dependabot[bot] <bot@users.noreply.github.com>", "created by Microsoft"):
            self.assertEqual(names(text), [], text)


class FixedSpans:
    """Stands in for the NER model: reports the given substrings as names."""

    def __init__(self, *names):
        self._names = names

    def find_names(self, text):
        return [Finding("person_name", text.index(name), text.index(name) + len(name)) for name in self._names]


class PlausibleNameFilterTest(unittest.TestCase):
    def kept(self, text, *reported):
        return [text[f.start:f.end] for f in PlausibleNameFilter(FixedSpans(*reported)).find_names(text)]

    def test_keeps_real_names(self):
        text = "Merci à Karim Benali, Emily O'Connor et DUPONT."

        self.assertEqual(self.kept(text, "Karim Benali", "Emily O'Connor", "DUPONT"),
                         ["Karim Benali", "Emily O'Connor", "DUPONT"])

    def test_drops_what_cannot_be_a_name(self):
        text = "drwxr-xr-x 1 devuser  see huggingface.co/Fastino/model, GLiNER2 and ONNX"

        self.assertEqual(self.kept(text, "devuser", "Fastino", "GLiNER2", "ONNX"), [])


if __name__ == "__main__":
    unittest.main()
