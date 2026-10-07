"""Prepare the pinned FP32 bundle from already evaluated artifacts; no install."""

import argparse
import hashlib
import shutil
import sys
from pathlib import Path
from urllib.request import urlopen

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from privacy_guard.service.distil_files import MANIFEST, REVISION, UPSTREAM


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=PROJECT / "evaluation/ner/models/distilcamembert-base-ner")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sources = {"config.json": "config.json", "model.onnx": "model_fp32.onnx",
               "tokenizer.json": "tokenizer.json"}
    for target, source in sources.items():
        if digest(args.source / source) != MANIFEST[target]:
            raise ValueError(f"Evaluated artifact mismatch: {source}")
    url = f"https://huggingface.co/{UPSTREAM}/resolve/{REVISION}/README.md"
    with urlopen(url, timeout=45) as stream:
        card = stream.read(256 * 1024 + 1)
    if hashlib.sha256(card).hexdigest() != MANIFEST["README.upstream.md"]:
        raise ValueError("Pinned upstream model card changed")
    for name, expected in MANIFEST.items():
        target = args.out / name
        if target.exists() and digest(target) != expected:
            raise ValueError(f"Refusing to overwrite an unrelated artifact: {name}")
    args.out.mkdir(parents=True, exist_ok=True)
    for target, source in sources.items():
        shutil.copyfile(args.source / source, args.out / target)
    (args.out / "README.upstream.md").write_bytes(card)
    print(f"Verified DistilCamemBERT FP32 bundle: {args.out.resolve()}")


if __name__ == "__main__":
    main()
