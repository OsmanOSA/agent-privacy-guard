"""Validate every saved prediction and summarize source-specific measurements."""

import json
from collections import Counter

import numpy as np

from .additional_cohort import RUN, SEED, TASKS
from .aggregate import latency
from .fetch import BASE, sha256
from .metrics import Metrics, character_positions
from .score import evaluate, load_rows


def bootstrap(corpus, predictions, kind, dataset):
    groups = {}
    for key, row in corpus.items():
        group = key if dataset == "deep-sequoia-nonwiki" else row["group"]
        metric = Metrics()
        metric.add(row["text"], [s for s in row["spans"] if s["kind"] == kind], predictions[key]["spans"])
        counts = [metric.counts[field] for field in ("exact_true_positives", "gold_entities", "predicted_entities", "fully_covered_entities")]
        groups.setdefault(group, np.zeros(4, dtype=np.int64))[:] += counts
    matrix = np.asarray([groups[key] for key in sorted(groups)])
    generator = np.random.default_rng(int(sha256(f"{SEED}:{dataset}:bootstrap".encode())[:8], 16))
    draws = generator.integers(0, len(matrix), size=(1000, len(matrix)))
    totals = matrix[draws].sum(axis=1)
    f1 = 2 * totals[:, 0] / np.maximum(totals[:, 1] + totals[:, 2], 1)
    coverage = totals[:, 3] / np.maximum(totals[:, 1], 1)
    return {"unit": "sentence" if dataset == "deep-sequoia-nonwiki" else "source-token block" if dataset == "europeana-newspapers-fr" else "source page",
            "groups": len(groups), "resamples": 1000,
            "exact_f1_95": np.quantile(f1, [.025, .975]).tolist(),
            "full_coverage_95": np.quantile(coverage, [.025, .975]).tolist()}, f1


def misses(corpus, predictions, kind):
    counts = Counter()
    for key, row in corpus.items():
        covered = character_positions(row["text"], predictions[key]["spans"])
        for span in row["spans"]:
            if span["kind"] != kind:
                continue
            expected = character_positions(row["text"], [span])
            status = "complete" if expected <= covered else "partial" if expected & covered else "entirely_missed"
            counts[status] += 1
    return dict(counts)


def main():
    run = json.loads((RUN / "run.json").read_text(encoding="utf-8"))
    cohort = json.loads((RUN / "cohort.json").read_text(encoding="utf-8"))
    if "finished_at" not in run or len(run["timing_orders"]) != 3:
        raise ValueError("Study has incomplete inference or timing")
    if sha256((RUN / "cohort.json").read_bytes()) != run["cohort_sha256"]:
        raise ValueError("Cohort was changed during inference")
    for filename in ("adapters.py", "additional_worker.py", "decode.py", "token_model.py", "unicode_offsets.py",
                     "score.py", "metrics.py", "license_policy.py"):
        frozen_hashes = run.get("execution_harness_hashes_at_resume", run["harness_hashes"])
        if sha256((BASE / filename).read_bytes()) != frozen_hashes[filename]:
            raise ValueError("Execution or scoring implementation changed during inference")
    corpora = {dataset: load_rows(RUN / f"{dataset}.jsonl") for dataset in TASKS}
    results, draws = {}, {}
    for name in run["models"]:
        report = json.loads((RUN / f"{name}.quality.json").read_text(encoding="utf-8"))
        if not report["complete"]:
            raise ValueError("Incomplete model prediction run")
        predictions = {dataset: load_rows(RUN / f"{name}.{dataset}.predictions.jsonl") for dataset in TASKS}
        timings, peaks = [], [report["peak_process_memory_bytes"]]
        for index in range(3):
            timed = json.loads((RUN / f"{name}.timing-{index}.json").read_text(encoding="utf-8"))
            peaks.append(timed["peak_process_memory_bytes"])
            for dataset in TASKS:
                observations = [r for r in timed["observations"] if r["dataset"] == dataset]
                expected = set(load_rows(RUN / f"{dataset}.timing.jsonl"))
                if len(observations) != len(expected) or {r["id"] for r in observations} != expected:
                    raise ValueError("Timing inputs missing or duplicated")
                for item in observations:
                    digest = sha256(json.dumps(predictions[dataset][item["id"]]["spans"], sort_keys=True).encode())
                    if digest != item["prediction_sha256"] or item["pass"] != index:
                        raise ValueError("Timing prediction differs from quality prediction")
            timings.extend(timed["observations"])
        datasets, draws[name] = {}, {}
        for dataset, kind in TASKS.items():
            fresh = evaluate(corpora[dataset], predictions[dataset], "test", kind)
            if fresh["quality"] != report["datasets"][dataset]["quality"]:
                raise ValueError("Saved score does not match reference and prediction files")
            confidence, draws[name][dataset] = bootstrap(corpora[dataset], predictions[dataset], kind, dataset)
            selected = [r for r in timings if r["dataset"] == dataset]
            bands = {"short_lt128": [r for r in selected if r["characters"] < 128],
                     "medium_128_511": [r for r in selected if 128 <= r["characters"] < 512],
                     "long_ge512": [r for r in selected if r["characters"] >= 512]}
            datasets[dataset] = {"task": kind, "quality": fresh["quality"], "confidence": confidence,
                "misses": misses(corpora[dataset], predictions[dataset], kind),
                "latency_ms": latency(selected), "latency_by_length": {band: latency(items) for band, items in bands.items() if items},
                "unique_timing_inputs_by_length": {band: len({r["id"] for r in items}) for band, items in bands.items() if items},
                "by_domain": report["datasets"][dataset]["by_domain"]}
        results[name] = {"backend": report["backend"], "threshold": report["threshold"],
                         "datasets": datasets, "peak_process_memory_bytes": max(peaks),
                         "timing_prediction_mismatches": 0}
    differences = {name: {dataset: np.quantile(draws[name][dataset] - draws["masker-mini"][dataset], [.025, .975]).tolist()
                         for dataset in TASKS} for name in results if name != "masker-mini"}
    summary = {"schema_version": 1, "run": run, "cohort": cohort, "models": results,
               "analysis_harness_hashes": {p.name: sha256(p.read_bytes()) for p in BASE.glob("*.py")},
               "window_audit": json.loads((BASE / "additional-window-audit.json").read_text(encoding="utf-8")),
               "tokenizer_audit": json.loads((BASE / "additional-tokenizer-audit.json").read_text(encoding="utf-8")),
               "overlap_audit": json.loads((BASE / "additional-overlap-audit.json").read_text(encoding="utf-8")),
               "paired_f1_difference_vs_masker_95": differences,
               "limitations": ["Transferred WikiNER thresholds, no new calibration or fine-tuning",
                    "Sequoia and Europeana PERSON scores have different annotation conventions",
                    "Europeana IO-derived contiguous spans, synthetic input boundaries, original source words",
                    "SoDUCo NAME_OR_BUSINESS is a diagnostic proxy for person-only deployments; no address model scores",
                    "No text-generation or fabricated personal values", "Training exposure remains unknown",
                    "Exploratory corpus subsamples; latency is local model inference, not hook latency"]}
    (BASE / "summary-additional-20261006.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: {dataset: result["quality"]["exact_f1"] for dataset, result in model["datasets"].items()}
                      for name, model in results.items()}, indent=2))


if __name__ == "__main__":
    main()
