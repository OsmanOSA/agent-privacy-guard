"""Persist the selected model requirement after a successful installation.

An absent marker means the explicit rules-only installation profile. A present
marker requires its exact model configuration; missing weights must fail closed.
Interface: requires_model(home), record_model(home), remove_model(home).
"""

import json
import os
import tempfile
from pathlib import Path

from privacy_guard.service.distil_files import REVISION, UPSTREAM
from privacy_guard.service.model_files import ModelFilesError

MARKER = "ner-model.json"
EXPECTED = {"model": UPSTREAM, "revision": REVISION, "variant": "onnx-fp32", "threshold": 0.5}


def requires_model(home: Path) -> bool:
    marker = home / MARKER
    if not marker.exists():
        return False
    try:
        if json.loads(marker.read_text(encoding="utf-8")) != EXPECTED:
            raise ValueError("Unknown model configuration")
    except (OSError, ValueError) as error:
        raise ModelFilesError("Installed NER configuration is invalid") from error
    return True


def record_model(home: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=home, prefix=".ner-model-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write((json.dumps(EXPECTED) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, home / MARKER)
    finally:
        temporary.unlink(missing_ok=True)


def remove_model(home: Path) -> None:
    (home / MARKER).unlink(missing_ok=True)
