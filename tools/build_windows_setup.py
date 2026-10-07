"""Build the Windows setup EXE; never install into the builder's account."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from windows_payload import build_payload, extract, fetch, longest_install_directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True, help='Verified DistilCamemBERT bundle')
    parser.add_argument('--lexicon', type=Path, help='Prepared public INSEE index and provenance sidecar')
    parser.add_argument('--work', type=Path, required=True, help='New build directory')
    parser.add_argument('--cache', type=Path, default=PROJECT / '.local-review/windows-setup/downloads')
    parser.add_argument('--out', type=Path, default=PROJECT / 'dist')
    parser.add_argument('--version', default='0.1.0-preview.1')
    parser.add_argument('--test-build', action='store_true', help='Separate application/registry identity')
    args = parser.parse_args()
    import re
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-z]+\.\d+)?', args.version):
        parser.error('Invalid version')
    payload = args.work.resolve() / 'payload'
    lock = build_payload(payload, args.cache.resolve(), args.model.resolve(), args.version, args.lexicon)
    compiler_root = args.work.resolve() / 'compiler'
    extract(fetch(lock['compiler'], args.cache.resolve()), compiler_root)
    compiler = compiler_root / 'nsis-3.12/makensis.exe'
    args.out.mkdir(parents=True, exist_ok=True)
    stem = 'PrivacyGuard-Test' if args.test_build else 'PrivacyGuard'
    output = args.out.resolve() / f'{stem}-{args.version}-windows-x64.exe'
    max_directory = longest_install_directory(payload, args.version)
    command = [str(compiler), '/V2', f'/DVERSION={args.version}', f'/DPAYLOAD={payload}',
               f'/DOUTPUT={output}', f'/DMAX_INSTDIR={max_directory}']
    if args.test_build:
        command.append('/DTEST_BUILD')
    command.append(str(PROJECT / 'packaging/windows/setup.nsi'))
    subprocess.run(command, check=True)
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    output.with_suffix('.exe.sha256').write_text(f'{digest}  {output.name}\n', encoding='ascii')
    print(json.dumps({'setup': str(output), 'sha256': digest, 'bytes': output.stat().st_size,
                      'max_install_directory': max_directory}))


if __name__ == '__main__':
    main()
