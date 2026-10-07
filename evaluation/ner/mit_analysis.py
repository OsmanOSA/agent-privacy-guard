"""Validate all nine new quality runs and twelve controlled timing series."""

import json

import numpy as np

from .additional_analysis import bootstrap, misses
from .additional_cohort import TASKS
from .aggregate import latency
from .fetch import BASE, sha256
from .mit_worker import RUN
from .score import evaluate, load_rows


def main():
    run = json.loads((RUN / "run.json").read_text(encoding="utf-8"))
    if "finished_at" not in run or len(run["timing_orders"]) != 3:
        raise ValueError("Quality or timing is incomplete")
    if sha256((RUN / "cohort.json").read_bytes()) != run["cohort_sha256"]:
        raise ValueError("Reference inputs changed")
    for filename in ("mit_adapters.py", "mit_worker.py", "mit_token_model.py", "mit_quality.py", "run_mit.py", "additional_worker.py",
                     "worker.py", "decode.py", "token_model.py", "unicode_offsets.py", "score.py", "metrics.py"):
        hashes = run.get("execution_harness_hashes_at_resume", run["harness_hashes"])
        if sha256((BASE / filename).read_bytes()) != hashes[filename]:
            raise ValueError(f"Execution implementation changed: {filename}")
    if sha256((BASE / "mit-candidates.json").read_bytes()) != run["registry_sha256"]:
        raise ValueError("Pinned candidate registry changed")
    if sha256((BASE / "mit-artifacts.json").read_bytes()) != run["artifacts_sha256"]:
        raise ValueError("Artifact receipt changed")
    corpora = {dataset: load_rows(RUN / f"{dataset}.jsonl") for dataset in TASKS}
    cohort = json.loads((RUN / "cohort.json").read_text(encoding="utf-8"))
    for dataset in TASKS:
        for suffix, field in (("", "quality_sha256"), (".timing", "timing_sha256")):
            if sha256((RUN / f"{dataset}{suffix}.jsonl").read_bytes()) != cohort["datasets"][dataset][field]:
                raise ValueError("Individual frozen input file changed")
    models, draws = {}, {}
    for name in run["timing_models"]:
        report = json.loads((RUN / f"{name}.quality.json").read_text(encoding="utf-8"))
        if not report["complete"]:
            raise ValueError("Incomplete quality results")
        predictions = {dataset: load_rows(RUN / f"{name}.{dataset}.predictions.jsonl") for dataset in TASKS}
        timings, peaks = [], [report["peak_process_memory_bytes"]]
        for index in range(3):
            timed = json.loads((RUN / f"{name}.timing-{index}.json").read_text(encoding="utf-8"))
            peaks.append(timed["peak_process_memory_bytes"])
            for dataset in TASKS:
                observations = [r for r in timed["observations"] if r["dataset"] == dataset]
                expected = set(load_rows(RUN / f"{dataset}.timing.jsonl"))
                if len(observations) != len(expected) or {r["id"] for r in observations} != expected:
                    raise ValueError("Missing or duplicate timing input")
                for item in observations:
                    digest = sha256(json.dumps(predictions[dataset][item["id"]]["spans"], sort_keys=True).encode())
                    if digest != item["prediction_sha256"] or item["pass"] != index:
                        raise ValueError("Timing predictions differ from quality predictions")
            timings.extend(timed["observations"])
        datasets, draws[name] = {}, {}
        for dataset, kind in TASKS.items():
            fresh = evaluate(corpora[dataset], predictions[dataset], "test", kind)["quality"]
            if fresh != report["datasets"][dataset]["quality"]:
                raise ValueError("Saved F1 does not match complete predictions")
            confidence, draws[name][dataset] = bootstrap(corpora[dataset], predictions[dataset], kind, dataset)
            datasets[dataset] = {"task": kind, "quality": fresh, "confidence": confidence,
                "misses": misses(corpora[dataset], predictions[dataset], kind),
                "latency_ms": latency([r for r in timings if r["dataset"] == dataset]),
                "by_domain": report["datasets"][dataset]["by_domain"]}
        models[name] = {"backend": report["backend"], "threshold": report["threshold"],
            "datasets": datasets, "peak_process_memory_bytes": max(peaks),
            "timing_prediction_mismatches": 0, "quality_predictions_sha256": {
                dataset: sha256((RUN / f"{name}.{dataset}.predictions.jsonl").read_bytes()) for dataset in TASKS}}
    reference = "distilcamembert-base-ner"
    differences = {name: {dataset: np.quantile(draws[name][dataset] - draws[reference][dataset], [.025, .975]).tolist()
        for dataset in TASKS} for name in run["models"]}
    result = {"schema_version": 1, "run": run, "cohort": cohort, "models": models,
        "normalization_audit": json.loads((BASE / "mit-normalization-audit.json").read_text(encoding="utf-8")),
        "paired_exact_f1_difference_vs_distil_95": differences,
        "limitations": ["PERSON only; SoDUCo NAME_OR_BUSINESS remains a separate diagnostic",
            "hmBERT trained on ICDAR-Europeana; its Europeana score is exposed, not independent",
            "Different native CPU backends: deployment comparison, not intrinsic architecture speed",
            "WikiNER threshold calibration reused for new models; no three-corpus test tuning",
            "spaCy confidence 1.0 is a sentinel; its native PER output has no calibrated span confidence",
            "DistilCamemBERT quality predictions reused unchanged; timing remeasured in this run",
            "Modern tokenizer natively deletes 14 private-use glyphs in 13 SoDUCo references; source and gold kept unchanged, no artificial span expansion",
            "Warm timing includes tokenization, all inference windows and decoding; excludes model loading and full hook",
            "No generated input or reference data; model training and evaluation data are distinct issues"]}
    (BASE / "summary-mit-20261006.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: {dataset: {"f1": item["quality"]["exact_f1"],
        "coverage": item["quality"]["full_entity_coverage"], "latency": item["latency_ms"]}
        for dataset, item in model["datasets"].items()} for name, model in models.items()}, indent=2))


if __name__ == "__main__":
    main()
