"""Build an allowlisted Windows payload from pinned public runtime artifacts."""

import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
# Not needed at run time: the documentation (68 MB, holding the 264-character path that
# failed installs under a long directory), C headers and import libraries, IDLE, pip.
UNUSED_RUNTIME = ('Doc', 'include', 'libs', 'Lib/idlelib', 'Lib/ensurepip')
# Windows MAX_PATH without long-path support, terminating null excluded.
MAX_PATH = 259


def longest_install_directory(payload, version):
    """How long the installation directory may be before a payload path exceeds MAX_PATH."""
    longest = max(len(p.relative_to(payload).as_posix()) for p in payload.rglob('*'))
    return MAX_PATH - len(f'\\versions\\{version}\\') - longest


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(row, cache):
    path = cache / row['filename']
    if not path.exists():
        cache.mkdir(parents=True, exist_ok=True)
        pending = path.with_suffix(path.suffix + '.partial')
        with urllib.request.urlopen(row['url'], timeout=90) as source, pending.open('wb') as target:
            shutil.copyfileobj(source, target)
        if digest(pending) != row['sha256']:
            raise ValueError(f"Download digest mismatch: {row['filename']}")
        pending.replace(path)
    if digest(path) != row['sha256']:
        raise ValueError(f"Cached artifact mismatch: {row['filename']}")
    return path


def extract(archive, target):
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            name = entry.filename
            destination = (target / name).resolve()
            if not destination.is_relative_to(target.resolve()) or '\\' in name:
                raise ValueError('Unsafe archive member')
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Archive symlinks are not supported')
        source.extractall(target)


def build_payload(target, cache, model, version, lexicon=None):
    from privacy_guard.service.distil_files import MANIFEST, REVISION, UPSTREAM
    if target.exists():
        raise ValueError('Use a new empty payload directory for each build')
    lock = json.loads((PROJECT / 'packaging/windows/dependencies.lock.json').read_text())
    runtime = target / 'runtime'
    runtime.mkdir(parents=True)
    extract(fetch(lock['python'], cache), runtime)
    for unused in UNUSED_RUNTIME:
        shutil.rmtree(runtime / unused)
    for wheel in lock['wheels']:
        extract(fetch(wheel, cache / 'wheels'), runtime / 'Lib/site-packages')
    (runtime / 'python314._pth').write_text(
        'Lib\nDLLs\n.\nLib/site-packages\n../app\nimport site\n', encoding='ascii')
    (runtime / 'privacy-guard-runtime.json').write_text(json.dumps(
        {'schema': 1, 'product': 'agent-privacy-guard', 'model_runtime': True}), encoding='ascii')
    for source in (PROJECT / 'privacy_guard').rglob('*.py'):
        dest = target / 'app' / source.relative_to(PROJECT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    shutil.copyfile(PROJECT / 'privacy_guard/claude_code/launcher.py', target / 'app/__main__.py')
    (target / 'model').mkdir()
    for name, expected in MANIFEST.items():
        if digest(model / name) != expected:
            raise ValueError(f'Name model mismatch: {name}')
        shutil.copyfile(model / name, target / 'model' / name)
    notices = target / 'notices'
    notices.mkdir()
    shutil.copyfile(PROJECT / 'LICENSE', notices / 'LICENSE-project.txt')
    shutil.copytree(PROJECT / 'licenses', notices / 'project-attributions')
    for row in lock.get('notices', []):
        shutil.copyfile(fetch(row, cache / 'notices'), notices / row['filename'])
    with zipfile.ZipFile(fetch(lock['compiler'], cache)) as compiler:
        (notices / 'NSIS-COPYING.txt').write_bytes(compiler.read('nsis-3.12/COPYING'))
    shutil.copyfile(PROJECT / 'packaging/windows/dependencies.lock.json', notices / 'dependencies.json')
    (notices / 'model.txt').write_text(
        f'{UPSTREAM}\nRevision: {REVISION}\nLicense: MIT (upstream model card).\n'
        'Changes: ONNX FP32 conversion, PERSON decoding and calibrated threshold.\n'
        'The complete upstream model card accompanies the weights.\n'
        'Dependency license files remain in runtime/Lib/site-packages/*.dist-info.\n', encoding='utf-8')
    if lexicon:
        provenance = json.loads(lexicon.with_suffix('.source.json').read_text(encoding='utf-8'))
        if digest(lexicon) != provenance['sqlite_sha256']:
            raise ValueError('INSEE lexicon does not match its preparation receipt')
        (target / 'data').mkdir()
        shutil.copyfile(lexicon, target / 'data/insee-names.sqlite')
        shutil.copyfile(lexicon.with_suffix('.source.json'), target / 'data/insee-names.source.json')
        shutil.copyfile(PROJECT / 'licenses/INSEE-data-NOTICE.txt', target / 'data/INSEE-data-NOTICE.txt')
    files = {p.relative_to(target).as_posix(): digest(p) for p in sorted(target.rglob('*')) if p.is_file()}
    (target / 'payload.json').write_text(json.dumps(
        {'schema': 1, 'product': 'agent-privacy-guard', 'version': version, 'files': files},
        indent=2) + '\n', encoding='utf-8')
    return lock
