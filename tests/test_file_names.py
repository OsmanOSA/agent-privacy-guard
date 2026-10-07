import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from privacy_guard.core.code_words import CODE_WORDS
from privacy_guard.core.detector import SensitiveDataDetector
from privacy_guard.core.file_names import FileNameDetector, has_file_name
from privacy_guard.core.insee_names import local_name_detector
from privacy_guard.core.name_lexicon import NameLexicon, normalize

# A tiny public-index stand-in. "test", "data" and "read" are listed as names on
# purpose: the real INSEE index lists them too.
GIVEN = ("camille", "marie", "julien", "test", "data", "read", "rose")
FAMILY = ("lefebvre", "dupont", "moreau", "data", "main", "report", "read")

# Identifier words the real index lists too: "name" and "per" as given names, "false"
# and "native" as family names.
GIVEN += ("name", "per")
FAMILY += ("false", "native")


class FileNameDetectorTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.path = self.home / "data" / "insee-names.sqlite"
        self.path.parent.mkdir()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("PRAGMA user_version=1")
            db.execute("CREATE TABLE names (kind TEXT, value TEXT, PRIMARY KEY(kind, value)) WITHOUT ROWID")
            db.executemany("INSERT INTO names VALUES (?, ?)",
                           [("given", normalize(v)) for v in GIVEN] + [("family", normalize(v)) for v in FAMILY])
            db.commit()
        self.detector = FileNameDetector(NameLexicon(self.path))

    def names(self, text):
        return [text[f.start:f.end] for f in self.detector.find_names(text)]

    def test_given_and_family_names_in_either_order(self):
        listing = "cv_camille_lefebvre.md\ncontrat-dupont-marie.pdf\nFacture_Julien_Moreau_2026-03.pdf"
        self.assertEqual(self.names(listing), ["camille_lefebvre", "dupont-marie", "Julien_Moreau"])

    def test_technical_file_names_are_not_names(self):
        for name in ("test_data.py", "read_data.py", "main_report.html", "rose_theme.css", "test_read_write.py",
                     "01-tool-name-false-positives.md", "per_native.py", "name_native.cu"):
            with self.subTest(name=name):
                self.assertEqual(self.names(name), [])

    def test_code_words_hold_no_common_name(self):
        common = ("camille", "marie", "julien", "thomas", "nicolas", "sophie", "lefebvre", "dupont",
                  "moreau", "girard", "martin", "bernard", "durand", "laurent", "petit", "garcia")
        self.assertEqual([name for name in common if name in CODE_WORDS], [])

    def test_words_outside_file_names_are_left_to_other_detectors(self):
        self.assertEqual(self.names("camille_lefebvre = 3"), [])
        self.assertFalse(has_file_name("camille lefebvre"))

    def test_lowercase_listing_reaches_name_detection_through_the_quick_detector(self):
        found = SensitiveDataDetector(local_name_detector(self.home)).find("documents/cv_camille_lefebvre.md")
        self.assertEqual(len([f for f in found if f.kind == "person_name"]), 1)


if __name__ == "__main__":
    unittest.main()
