"""INSEE complement: contextual names, exact restoration and bounded ambiguity."""

import sqlite3
import hashlib
import io
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from zipfile import ZipFile

from privacy_guard.core.detector import SensitiveDataDetector
from privacy_guard.core.insee_names import InseeNameDetector, local_name_detector
from privacy_guard.core.name_lexicon import normalize
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from tests.fakes import ReversingCipher
from tools.prepare_insee_lexicon import build


class InseeNamesTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'data' / 'insee-names.sqlite'
        self.path.parent.mkdir()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('PRAGMA user_version=1')
            db.execute('CREATE TABLE names (kind TEXT, value TEXT, PRIMARY KEY(kind, value)) WITHOUT ROWID')
            db.executemany('INSERT INTO names VALUES (?, ?)',
                           [(kind, normalize(name)) for kind, names in {
                               'given': ['Alice', 'Élodie', 'Rose', 'Pierre', 'Anne-Marie'],
                               'family': ['Martin', 'Dupont', "O'Connor", 'Le Gall'],
                           }.items() for name in names])
            db.commit()
        self.names = local_name_detector(self.root)

    def values(self, text):
        return [text[f.start:f.end] for f in SensitiveDataDetector(self.names).find(text)]

    def test_lowercase_person_fields_and_exact_restoration(self):
        text = '{"first_name": "alice", "last_name": "dupont"}'
        vault = VaultStore(self.root / 'vault', ReversingCipher()).session('a')
        core = PrivacyCore(vault, self.names)
        protected, counts = core.protect_with_counts(text)
        self.assertEqual(counts, {'person_name': 2})
        self.assertNotIn('alice', protected)
        self.assertEqual(core.restore(protected), text)

    def test_given_family_and_full_names(self):
        for text, expected in [
            ('prénom: ÉLODIE', ['ÉLODIE']), ('prénom: elodie', ['elodie']),
            ('nom de famille: le gall', ['le gall']),
            ('full_name="alice martin"', ['alice martin']),
            ('signé par alice martin.', ['alice martin']),
            ('prénom: anne-marie', ['anne-marie']),
            ('surname="o’connor"', ['o’connor']),
        ]:
            with self.subTest(text=text):
                self.assertEqual(self.values(text), expected)

    def test_dictionary_words_without_person_context_are_unchanged(self):
        for text in ['une rose pousse sur la pierre', 'Rose et Pierre sont des mots ambigus.',
                     'rose.py', 'alice_helper = 1', 'name="Rose"', 'tokens_estimated=tokens_estimated']:
            self.assertEqual(InseeNameDetector(self.path).find_names(text), [], text)

    def test_partial_words_and_identifiers_are_not_names(self):
        for text in ['prénom: alicex', 'prénom: alice_helper', 'first_name="alice2"',
                     'surname="dupont-dev"', 'prénom: alice inattendue']:
            self.assertEqual(InseeNameDetector(self.path).find_names(text), [], text)

    def test_insee_never_vetoes_other_detectors(self):
        self.assertEqual(self.values('Nom : Xyliana Zorvax'), ['Xyliana Zorvax'])

    def test_propagation_keeps_same_output_consistent(self):
        self.assertEqual(self.values("prénom: alice\nusers=['alice', 'ALICE']"),
                         ['alice', 'alice', 'ALICE'])

    def test_escaped_json_newline_still_separates_contexts(self):
        text = r'{"first_name":"alice"}\n{"last_name":"dupont"}'
        self.assertEqual(self.values(text), ['alice', 'dupont'])

    def test_missing_optional_file_keeps_heuristic(self):
        self.assertEqual(local_name_detector(self.root / 'absent').find_names('first_name="alice"'), [])

    def test_no_context_never_opens_database(self):
        self.path.unlink()
        self.assertEqual(InseeNameDetector(self.path).find_names('print("hello")'), [])

    def test_existing_corrupt_database_is_not_silently_ignored(self):
        self.path.write_bytes(b'not a database')
        with self.assertRaises(sqlite3.DatabaseError):
            self.names.find_names('prénom: alice')

    def test_combining_accent_and_apostrophe_normalization(self):
        self.assertEqual(normalize('  E\u0301LODIE  '), 'elodie')
        self.assertEqual(normalize('O’Connor'), "o'connor")

    def sources(self):
        sources = []
        for kind, content in [('given', 'prenom\nALICE\nalice\nÉLODIE\n_PRENOMS_RARES\n'),
                              ('family', 'NOM\nMARTIN\nAUTRES NOMS\n')]:
            data = io.BytesIO()
            with ZipFile(data, 'w') as archive:
                archive.writestr('names.csv', content)
            (self.root / f'{kind}.zip').write_bytes(data.getvalue())
            sources.append(dict(kind=kind, archive=f'{kind}.zip', member='names.csv',
                                column='prenom' if kind == 'given' else 'NOM', delimiter=';',
                                sha256=hashlib.sha256(data.getvalue()).hexdigest()))
        return sources

    def test_preparation_deduplicates_and_excludes_suppression_categories(self):
        metadata = build(self.root, self.path, self.sources())
        self.assertEqual(metadata['unique_normalized_names'], {'given': 2, 'family': 1})
        self.assertTrue(self.path.with_suffix('.source.json').exists())
        self.assertEqual(self.values('prénom: alice'), ['alice'])

    def test_changed_archive_preserves_existing_index(self):
        original = self.path.read_bytes()
        sources = self.sources()
        (self.root / 'given.zip').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            build(self.root, self.path, sources)
        self.assertEqual(self.path.read_bytes(), original)

    def test_installed_service_factory_uses_its_own_guard_home(self):
        from privacy_guard.service.__main__ import _load_detector
        detector = _load_detector(self.root / 'logs/service.log', self.root / 'models/absent')
        self.assertEqual([f.kind for f in detector.find_names('prénom: alice')], ['person_name'])

    def test_long_lowercase_code_without_context_has_no_findings(self):
        self.assertEqual(self.values('alice_helper = 1\n' * 2000), [])


if __name__ == '__main__':
    unittest.main()
