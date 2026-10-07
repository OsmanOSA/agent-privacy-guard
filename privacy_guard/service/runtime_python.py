"""Choose the bundled interpreter when running a self-contained Windows setup."""

import json
from pathlib import Path


def bundled_python(executable: str) -> Path | None:
    python = Path(executable)
    try:
        marker = json.loads((python.parent / 'privacy-guard-runtime.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if marker == {'schema': 1, 'product': 'agent-privacy-guard', 'model_runtime': True}:
        return python
    return None
