"""Prepares the converted name model for publication on Hugging Face.

Copies the installed model files into a release folder, checks them against the
SHA-256 manifest the installer enforces, and writes the model card (README.md)
with the license attribution the original model requires.

Standard library only:
    python tools/prepare_model_release.py [--out DIRECTORY]

The release goes outside the project by default: the project folder may be
synchronised (OneDrive...), and 280 MB of model have nothing to do there.

Publishing stays a deliberate step, under the publisher's own account:
    pip install huggingface_hub
    hf auth login
    hf upload <account>/privacy-guard-person-ner ~/.privacy-guard/release/person-ner .
Then set DEFAULT_MODEL_SOURCE in privacy_guard/service/name_model_setup.py to
    https://huggingface.co/<account>/privacy-guard-person-ner/resolve/main
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from privacy_guard.service.model_files import DEFAULT_MODEL_DIR, MANIFEST, ModelFiles  # noqa: E402

MODEL_CARD = """\
---
license: apache-2.0
language: [en, fr, es, de, it, pt, nl]
library_name: onnxruntime
pipeline_tag: token-classification
base_model: fastino/gliner2-privacy-filter-PII-multi
tags: [pii, ner, privacy, onnx, gliner2]
---

# Privacy Guard - person name detector (ONNX, 4-bit)

Finds person names in free text, locally, to keep them out of what AI coding
agents send to their models. Used by the background service of Agent Privacy Guard.

## What this is

A conversion of [fastino/gliner2-privacy-filter-PII-multi](https://huggingface.co/fastino/gliner2-privacy-filter-PII-multi)
(GLiNER2-PII, Apache-2.0), restricted to the single label `person`:

- one ONNX graph: mDeBERTa-v3 encoder, span representations, count prediction
  and the `person` projection;
- 4-bit weight-only quantization (block size 32): activations stay in full
  precision, which preserves this DeBERTa-v3 model's outputs where classic
  dynamic int8 quantization does not;
- runs with `onnxruntime`, `tokenizers` and `numpy`, without PyTorch.

| | Original (PyTorch) | This model |
|---|---|---|
| Size | 1.2 GB | 0.27 GB |
| Load time (CPU) | ~10 s | ~1.7 s |
| Memory | ~1.8 GB | ~0.5 GB |

## Validation

Text preparation and decoding are reimplemented without PyTorch. On every text
of the validation set (French and English: letters, customer records, CVs, and
traps such as cities, companies and street names), both the model input (token
ids) and the result (names and character offsets) are identical to the original
model's. See `tools/validate_name_model.py` in the Agent Privacy Guard repository.

## Files

| File | SHA-256 |
|---|---|
{hashes}

`config.json` holds the constant question prefix and marker positions captured
from GLiNER2's own preprocessing, plus the span width and threshold.

## Limitations

- Only the `person` label; other personal data is detected by deterministic rules.
- Trained on seven languages (en, fr, es, de, it, pt, nl).
- May mistake identifiers for people in source code: Agent Privacy Guard only
  runs it on documents.

## License and attribution

Apache-2.0, as the original model. Derived from
[fastino/gliner2-privacy-filter-PII-multi](https://huggingface.co/fastino/gliner2-privacy-filter-PII-multi)
by Fastino, built on [microsoft/mdeberta-v3-base](https://huggingface.co/microsoft/mdeberta-v3-base) (MIT).
Changes: conversion to ONNX, restriction to the `person` label, 4-bit weight-only quantization.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path.home() / ".privacy-guard" / "release" / "person-ner")
    args = parser.parse_args()

    if not ModelFiles(DEFAULT_MODEL_DIR).is_ready():
        print(f"✗ {DEFAULT_MODEL_DIR} does not hold the validated model (SHA-256 mismatch or missing file).")
        return 1

    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    for name in MANIFEST:
        shutil.copyfile(DEFAULT_MODEL_DIR / name, args.out / name)

    hashes = "\n".join(f"| `{name}` | `{digest}` |" for name, digest in MANIFEST.items())
    (args.out / "README.md").write_text(MODEL_CARD.replace("{hashes}", hashes), encoding="utf-8")
    print(f"✓ Release ready in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
