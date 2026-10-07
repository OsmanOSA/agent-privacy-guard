"""Freeze real-source calibration, quality and timing samples before inference."""

import hashlib
import json
from collections import Counter

from .fetch import BASE, sha256
from .license_policy import require_eligible_corpus
from .score import load_rows

RUN_DIR = BASE / "results" / "comparison-20261005"
SEED = "privacy-guard-french-ner-20261005-v1"


def ordered(rows, purpose):
    return sorted(rows, key=lambda r: hashlib.sha256(
        f"{SEED}:{purpose}:{r['id']}".encode()).hexdigest())


def main():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    source = BASE / "data/prepared/wikiner-fr-gold.jsonl"
    rows = list(load_rows(source).values())
    require_eligible_corpus(rows)
    calibration = ordered([r for r in rows if r["split"] == "calibration"], "calibration")[:512]
    quality = ordered([r for r in rows if r["split"] == "test"], "quality")[:2000]
    timing = ordered(quality, "timing")[:300]
    manifest = {"seed": SEED, "source_sha256": sha256(source.read_bytes()),
                "purpose": "Initial person recognition comparison; not the full gold corpus.",
                "cpu_threads": 4, "threshold_grid": [0.15, 0.25, 0.4, 0.5, 0.6],
                "selection_metric": "exact_f1; ties resolved by full coverage then precision",
                "timing_passes": 3, "samples": {}}
    for name, sample in (("calibration", calibration), ("quality", quality), ("timing", timing)):
        target = RUN_DIR / f"{name}.jsonl"
        content = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in sample)
        if target.exists() and target.read_text(encoding="utf-8") != content:
            raise ValueError("A frozen cohort must not be replaced")
        target.write_text(content, encoding="utf-8", newline="\n")
        manifest["samples"][name] = {"records": len(sample), "sha256": sha256(target.read_bytes()),
                                     "person_mentions": sum(s["kind"] == "PERSON" for r in sample for s in r["spans"]),
                                     "negative_records": sum(not any(s["kind"] == "PERSON" for s in r["spans"]) for r in sample),
                                     "length_bands": dict(Counter(length_band(r["text"]) for r in sample))}
    (RUN_DIR / "cohort.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


def length_band(text):
    return "short_lt128" if len(text) < 128 else "medium_128_511" if len(text) < 512 else "long_ge512"


if __name__ == "__main__":
    main()
