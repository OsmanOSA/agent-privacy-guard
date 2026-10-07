"""Explicit offline preparation: official INSEE ZIPs to an indexed public lexicon.

Example: python tools/prepare_insee_lexicon.py --output evaluation/ner/data/insee/data/insee-names.sqlite
No download occurs in hooks. Pinned sources must be reviewed before updating.
"""

import argparse
import csv
import hashlib
import io
import json
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
from privacy_guard.core.name_lexicon import SCHEMA_VERSION, normalize

SOURCES = [
    dict(kind='given', archive='given.zip', member='prenoms-2025-liste.csv',
         url='https://www.insee.fr/fr/statistiques/fichier/8595130/prenoms-2025-liste_csv.zip',
         page='https://www.insee.fr/fr/statistiques/8595130', published='2026-07-16',
         coverage='Births in France, 1900-2025; given at least three times',
         sha256='3a85c26c4932af016c3dfc8212e3e739092f1f51f21821b2e36f1d4fd3e8c283',
         delimiter=';', column='prenom'),
    dict(kind='family', archive='family.zip', member='noms2008nat_txt.txt',
         url='https://www.insee.fr/fr/statistiques/fichier/3536630/noms2008nat_txt.zip',
         page='https://www.insee.fr/fr/statistiques/3536630', published='2018-05-22',
         coverage='Births in France, 1891-2000; surname given at least thirty times',
         sha256='c8693ff69bed32621250f1fc06e71b686e72bba1dbd771055e431d305527cfba',
         delimiter='\t', column='NOM'),
]
TERMS = 'https://www.insee.fr/fr/outil-interactif/7737357/legal-notice.html'
MAX_ARCHIVE = 8 * 1024 * 1024
MAX_MEMBER = 50 * 1024 * 1024


def archive_bytes(directory, source):
    path = directory / source['archive']
    if path.exists():
        if path.stat().st_size > MAX_ARCHIVE:
            raise ValueError('INSEE archive exceeds preparation limit')
        data = path.read_bytes()
    else:
        request = Request(source['url'], headers={'User-Agent': 'PrivacyGuard-INSEE-study/1.0'})
        with urlopen(request, timeout=60) as response:
            data = response.read(MAX_ARCHIVE + 1)
        if len(data) > MAX_ARCHIVE:
            raise ValueError('INSEE archive exceeds preparation limit')
    if hashlib.sha256(data).hexdigest() != source['sha256']:
        raise ValueError('INSEE source changed: review the pinned edition before importing')
    directory.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(data)
    return data


def read_names(data, source):
    with ZipFile(io.BytesIO(data)) as archive:
        member = archive.getinfo(source['member'])
        if member.file_size > MAX_MEMBER:
            raise ValueError('INSEE member exceeds preparation limit')
        content = archive.read(member).decode('utf-8-sig')
    rows = csv.DictReader(io.StringIO(content), delimiter=source['delimiter'])
    if source['column'] not in (rows.fieldnames or []):
        raise ValueError('Unexpected INSEE columns')
    for row in rows:
        name = normalize(row[source['column']])
        # Aggregate suppression categories are not names.
        if name and not name.startswith('_') and name not in {'autres noms', 'prenoms rares'}:
            yield source['kind'], name


def build(directory, output, sources=SOURCES):
    inputs = [(source, archive_bytes(directory, source)) for source in sources]
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.insee-', suffix='.sqlite', dir=output.parent)
    os.close(handle)
    try:
        with closing(sqlite3.connect(temporary)) as db:
            db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
            db.execute('CREATE TABLE names (kind TEXT, value TEXT, PRIMARY KEY(kind, value)) WITHOUT ROWID')
            db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)')
            for source, data in inputs:
                db.executemany('INSERT OR IGNORE INTO names VALUES (?, ?)', read_names(data, source))
            counts = dict(db.execute('SELECT kind, count(*) FROM names GROUP BY kind'))
            if not counts.get('given') or not counts.get('family'):
                raise ValueError('Both INSEE name categories must be populated')
            metadata = dict(producer='INSEE', prepared_utc=datetime.now(timezone.utc).isoformat(),
                            sources=sources, unique_normalized_names=counts, terms_url=TERMS,
                            reuse='INSEE data reuse terms; attribution and integrity required; code MIT is separate',
                            transformation='Case/accent/apostrophe/space folding, deduplication; no sex or birth counts',
                            scope='Public name lexicon, not an annotated evaluation corpus or completeness guarantee')
            db.execute('INSERT INTO metadata VALUES (?, ?)', ('provenance', json.dumps(metadata)))
            db.commit()
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    metadata['sqlite_sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    metadata['sqlite_bytes'] = output.stat().st_size
    output.with_suffix('.source.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archives-dir', type=Path, default=PROJECT / 'evaluation/ner/data/insee')
    parser.add_argument('--output', type=Path, required=True, help='Explicit destination; no automatic global installation')
    args = parser.parse_args()
    print(json.dumps(build(args.archives_dir, args.output), indent=2))


if __name__ == '__main__':
    main()
