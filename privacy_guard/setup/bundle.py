"""Verify a self-contained Windows payload before changing a user installation.

Interface: verify_bundle(bundle) -> manifest, check_runtime(bundle)
"""

import hashlib
import json
import subprocess
from pathlib import Path

from privacy_guard.setup.errors import DOWNLOAD_AGAIN, SetupError

# The probe exits with a cause code instead of a traceback: its stderr used to be
# discarded, which hid a memory allocation failure behind a generic message.
_PROBE = '''
import sys
try:
    import numpy, onnxruntime, tokenizers
    from pathlib import Path
    from privacy_guard.service.distil_name_detector import DistilNameDetector
    from privacy_guard.service.model_files import ModelFilesError
except Exception:
    sys.exit(13)
try:
    detector = DistilNameDetector(Path(sys.argv[1]))
    assert detector.find_names("Madame Sophie Martin habite Paris.")
except MemoryError:
    sys.exit(11)
except (FileNotFoundError, ModelFilesError):
    sys.exit(12)
except Exception as error:
    # ONNX Runtime reports exhausted memory as "bad allocation".
    sys.exit(11 if "alloc" in str(error).lower() else 13)
'''
_PROBE_FAILURES = {
    11: "Le modèle de noms n’a pas pu démarrer : mémoire insuffisante. "
        "Fermez des applications, puis relancez l’installation.",
    12: f"Le modèle de noms est incomplet : {DOWNLOAD_AGAIN}",
    13: "Le modèle de noms n’a pas pu démarrer sur cet ordinateur "
        "(bibliothèque système manquante ou bloquée).",
}


def verify_bundle(bundle: Path):
    manifest = json.loads((bundle / 'payload.json').read_text(encoding='utf-8'))
    if manifest.get('product') != 'agent-privacy-guard' or manifest.get('schema') != 1:
        raise SetupError(f'Contenu d’installation inconnu : {DOWNLOAD_AGAIN}')
    files = manifest.get('files')
    if not isinstance(files, dict) or not files:
        raise SetupError(f'Contenu d’installation incomplet : {DOWNLOAD_AGAIN}')
    for name, expected in files.items():
        target = (bundle / name).resolve()
        if not target.is_relative_to(bundle.resolve()):
            raise SetupError(f'Contenu d’installation invalide : {DOWNLOAD_AGAIN}')
        with target.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise SetupError(f'Fichier d’installation altéré ({name}) : {DOWNLOAD_AGAIN}')
    return manifest


def check_runtime(bundle: Path):
    result = subprocess.run([str(bundle / 'runtime/python.exe'), '-c', _PROBE,
                             str(bundle / 'model')], capture_output=True, timeout=90,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise SetupError(_PROBE_FAILURES.get(result.returncode, _PROBE_FAILURES[13]))
