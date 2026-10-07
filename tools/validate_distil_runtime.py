"""Compare deployed decoding with frozen real-corpus predictions, without retraining."""

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from evaluation.ner.additional_cohort import RAW, RUN, TASKS
from evaluation.ner.fetch import BASE, sha256
from privacy_guard.service.distil_name_detector import DistilNameDetector


def load(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    args = parser.parse_args()
    detector = DistilNameDetector(args.model_dir)
    checked = {}
    for corpus in ["deep-sequoia-nonwiki", "europeana-newspapers-fr", "soduco-nested-ner"]:
        predictions = {r["id"]: r for r in load(RUN / f"distilcamembert-base-ner.{corpus}.predictions.jsonl")}
        rows = load(RUN / f"{corpus}.timing.jsonl")[:12]
        for row in rows:
            expected = predictions[row["id"]]
            assert sha256(row["text"].encode()) == expected["text_sha256"]
            actual = [{"kind": TASKS[corpus], "start": f.start, "end": f.end} for f in detector.find_names(row["text"])]
            assert actual == expected["spans"], f"Prediction drift: {corpus}/{row['id']}"
        checked[corpus] = len(rows)
    reference = json.loads((BASE / "latency-length-20261006.json").read_text(encoding="utf-8"))
    source = RAW / "europeana.bio"
    assert sha256(source.read_bytes()) == reference["source_sha256"]
    text = " ".join(line.rsplit(None, 1)[0] for line in source.read_text(encoding="utf-8").splitlines() if line.strip())
    case = reference["cases"][-1]
    text = text[:case["characters"]]
    assert sha256(text.encode()) == case["text_sha256"]
    findings = detector.find_names(text)
    expected = json.loads((BASE / "latency-cache-20261006.json").read_text(encoding="utf-8"))
    assert sha256(json.dumps([(f.kind, f.start, f.end) for f in findings]).encode()) == expected["prediction_sha256"]
    report = {"checked_real_corpus_inputs": checked, "long_input_tokens": case["tokens"],
              "long_input_windows": case["windows"], "long_input_findings": len(findings),
              "prediction_drift": 0, "model_dir": args.model_dir.name}
    (BASE / "distil-runtime-validation-20261006.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
