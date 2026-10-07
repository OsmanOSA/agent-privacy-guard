"""Validate complete runs and summarize quality uncertainty and execution cost."""

import json

import numpy as np

from .cohort import RUN_DIR, SEED, length_band
from .fetch import BASE, sha256
from .metrics import Metrics
from .error_analysis import coverage_errors
from .score import evaluate, load_rows


def read(name):
    return json.loads((RUN_DIR / name).read_text(encoding="utf-8"))


def confidence(corpus, predictions, draws):
    counts = []
    for key, row in corpus.items():
        metric = Metrics()
        metric.add(row["text"], [s for s in row["spans"] if s["kind"] == "PERSON"], predictions[key]["spans"])
        counts.append([metric.counts[field] for field in ("exact_true_positives", "gold_entities", "predicted_entities", "fully_covered_entities")])
    totals = np.asarray(counts, dtype=np.int64)[draws].sum(axis=1)
    f1 = 2 * totals[:, 0] / np.maximum(totals[:, 1] + totals[:, 2], 1)
    coverage = totals[:, 3] / np.maximum(totals[:, 1], 1)
    intervals = {"exact_f1": np.quantile(f1, [.025, .975]).tolist(),
                 "full_entity_coverage": np.quantile(coverage, [.025, .975]).tolist()}
    return intervals, {"exact_f1": f1, "full_entity_coverage": coverage}


def latency(observations):
    times = np.asarray([row["elapsed_ms"] for row in observations])
    return {"observations": len(times), "p50": float(np.median(times)),
            "p95": float(np.quantile(times, .95, method="inverted_cdf")),
            "mean": float(times.mean()), "sum": float(times.sum()),
            "texts_per_second": float(1000 / times.mean())}


def main():
    run, cohort, independent = read("run.json"), read("cohort.json"), read("independent-cohort.json")
    if "finished_at" not in run or len(run["timing_model_orders"]) != 3:
        raise ValueError("Controlled comparison is incomplete")
    corpora = {"wikiner": load_rows(RUN_DIR / "quality.jsonl"), "fenec": load_rows(RUN_DIR / "independent.jsonl")}
    generator = np.random.default_rng(int(sha256(SEED.encode())[:8], 16))
    draws = {key: generator.integers(0, len(rows), size=(1000, len(rows))) for key, rows in corpora.items()}
    models, bootstraps = {}, {}
    for name in run["quality_model_order"]:
        quality, other = read(f"{name}.quality.json"), read(f"{name}.independent.json")
        predictions = {"wikiner": load_rows(RUN_DIR / f"{name}.predictions.jsonl"),
                       "fenec": load_rows(RUN_DIR / f"{name}.independent.predictions.jsonl")}
        intervals, samples = {}, {}
        for key, rows in corpora.items():
            fresh = evaluate(rows, predictions[key], "test", "PERSON")["quality"]
            expected = quality["calibrated"]["quality"] if key == "wikiner" else other["quality"]
            if fresh != expected:
                raise ValueError("Aggregate score validation failed")
            intervals[key], samples[key] = confidence(rows, predictions[key], draws[key])
        passes = [read(f"{name}.timing-{index}.json") for index in range(3)]
        timings, mismatch = [], 0
        expected_ids = set(load_rows(RUN_DIR / "timing.jsonl"))
        for index, measured in enumerate(passes):
            items = measured["observations"]
            if len(items) != 300 or {r["id"] for r in items} != expected_ids or measured["pass"] != index:
                raise ValueError("Timing pass has missing or duplicate inputs")
            for item in items:
                expected = sha256(json.dumps(predictions["wikiner"][item["id"]]["spans"], sort_keys=True).encode())
                mismatch += expected != item["prediction_sha256"]
            timings.extend(items)
        if mismatch:
            raise ValueError("Timing predictions differ from the quality run")
        bands = {band: latency([r for r in timings if r["length_band"] == band]) for band in {r["length_band"] for r in timings}}
        breakdown = {}
        for band in {length_band(row["text"]) for row in corpora["wikiner"].values()}:
            selected = {key: row for key, row in corpora["wikiner"].items() if length_band(row["text"]) == band}
            breakdown[band] = evaluate(selected, {key: predictions["wikiner"][key] for key in selected}, "test", "PERSON")["quality"]
        models[name] = {"backend": passes[0]["backend"], "threshold": quality["selected_threshold"],
            "wikiner": quality["calibrated"]["quality"], "common_threshold_0_5": quality["common_threshold_0_5"]["quality"],
            "fenec": other["quality"], "fenec_by_dataset": other["by_dataset"],
            "fenec_individual_person_only": other["individual_person_only"], "confidence_95": intervals,
            "coverage_errors": {key: coverage_errors(corpora[key], predictions[key]) for key in corpora},
            "latency_ms": latency(timings), "latency_by_length": bands, "wikiner_by_length": breakdown,
            "latency_by_pass": [latency(p["observations"]) for p in passes],
            "model_load_ms_by_pass": [p["startup_model_load_ms"] for p in passes],
            "peak_process_memory_bytes": max(p["peak_process_memory_bytes"] for p in passes),
            "weights_bytes": quality["weights_bytes"], "artifact_sha256": run["active_artifacts"][name]["sha256"],
            "timing_prediction_mismatches": mismatch, "timing_process_cpu_seconds": sum(p["process_cpu_seconds"] for p in passes)}
        bootstraps[name] = samples
    reference = "masker-mini"
    differences = {name: {key: {metric: np.quantile(samples[key][metric] - bootstraps[reference][key][metric], [.025, .975]).tolist()
                    for metric in samples[key]} for key in corpora} for name, samples in bootstraps.items() if name != reference}
    report = {"schema_version": 1, "study": "comparison-20261005", "run": run,
        "analysis_harness_hashes": {p.name: sha256(p.read_bytes()) for p in BASE.glob("*.py")},
        "wikiner_cohort": cohort, "fenec_cohort": independent, "models": models,
        "paired_bootstrap": {"reference": reference, "resamples": 1000, "unit": "WikiNER sentence or FENEC document",
                             "difference_confidence_95": differences},
        "limitations": ["PERSON only; not comprehensive PII", "WikiNER exposure disclosed by Masker and DistilCamemBERT",
            "FENEC is a six-document subset, not the full corpus; pretraining overlap remains possible",
            "FENEC includes collective person labels with different conventions", "Timing is local inference, not the full hook workflow",
            "Different deployable backends and precision; not intrinsic architecture speed", "Only one unique long WikiNER timing input"]}
    (BASE / "summary-20261005.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: {"F1": m["wikiner"]["exact_f1"], "coverage": m["wikiner"]["full_entity_coverage"],
                      "FENEC_F1": m["fenec"]["exact_f1"], "p50_ms": m["latency_ms"]["p50"],
                      "p95_ms": m["latency_ms"]["p95"]} for name, m in models.items()}, indent=2))


if __name__ == "__main__":
    main()
