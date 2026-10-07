"""Score complete per-record predictions against one prepared corpus split."""

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

from .metrics import Metrics, validate_spans
from .license_policy import require_eligible_corpus


def load_rows(path):
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["id"] in rows:
            raise ValueError("Duplicate record ID")
        rows[row["id"]] = row
    return rows


def evaluate(corpus, predictions, split, kind):
    require_eligible_corpus(corpus.values())
    expected = {key: row for key, row in corpus.items() if row["split"] == split}
    if not expected or expected.keys() != predictions.keys():
        raise ValueError("Predictions must cover exactly every record in the selected split")
    metrics, timings = Metrics(), []
    for key, row in expected.items():
        prediction = predictions[key]
        digest = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
        if prediction.get("text_sha256") != digest:
            raise ValueError("Prediction text fingerprint does not match the corpus")
        validate_spans(row["text"], prediction["spans"])
        gold = [span for span in row["spans"] if span["kind"] == kind]
        found = [span for span in prediction["spans"] if span["kind"] == kind]
        metrics.add(row["text"], gold, found)
        elapsed = prediction.get("elapsed_ms")
        if elapsed is not None:
            if not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError("Latency must be finite and non-negative")
            timings.append(elapsed)
    if timings and len(timings) != len(expected):
        raise ValueError("Timing must cover all evaluated records or be absent everywhere")
    report = {"split": split, "kind": kind, "quality": metrics.report()}
    if timings:
        ordered = sorted(timings)
        report["latency_ms"] = {"p50": statistics.median(timings),
                                "p95": ordered[math.ceil(len(timings) * 0.95) - 1],
                                "sum": sum(timings), "observations": len(timings)}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--split", choices=("calibration", "test"), default="test")
    parser.add_argument("--kind", default="PERSON")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(load_rows(args.corpus), load_rows(args.predictions), args.split, args.kind)
    report["corpus_sha256"] = hashlib.sha256(args.corpus.read_bytes()).hexdigest()
    report["predictions_sha256"] = hashlib.sha256(args.predictions.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
