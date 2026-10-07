"""Verify a self-contained Windows payload before changing a user installation."""

import hashlib
import json
import subprocess
from pathlib import Path


def verify_bundle(bundle: Path):
    manifest = json.loads((bundle / 'payload.json').read_text(encoding='utf-8'))
    if manifest.get('product') != 'agent-privacy-guard' or manifest.get('schema') != 1:
        raise ValueError('Unknown setup payload')
    files = manifest.get('files')
    if not isinstance(files, dict) or not files:
        raise ValueError('Missing setup inventory')
    for name, expected in files.items():
        target = (bundle / name).resolve()
        if not target.is_relative_to(bundle.resolve()):
            raise ValueError('Invalid payload path')
        with target.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise ValueError(f'Setup file failed verification: {name}')
    return manifest


def check_runtime(bundle: Path):
    code = ('import numpy, onnxruntime, tokenizers; '
            'from privacy_guard.service.distil_name_detector import DistilNameDetector; '
            'from pathlib import Path; import sys; '
            'd=DistilNameDetector(Path(sys.argv[1])); '
            'assert d.find_names("Madame Sophie Martin habite Paris.")')
    result = subprocess.run([str(bundle / 'runtime/python.exe'), '-c', code,
                             str(bundle / 'model')], capture_output=True, timeout=90,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('The bundled name detector could not run on this computer')
