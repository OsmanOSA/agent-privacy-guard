"""Evaluate one model in one isolated CPU process with no prediction cache."""

import argparse
import hashlib
import json
import random
import time

from .adapters import load_model
from .cohort import RUN_DIR, SEED, length_band
from .decode import decode
from .fetch import BASE, sha256
from .metrics import Metrics
from .runtime_info import peak_memory_bytes, versions
from .score import evaluate, load_rows


def verify_cohort():
    manifest = json.loads((RUN_DIR / "cohort.json").read_text(encoding="utf-8"))
    for name, info in manifest["samples"].items():
        if sha256((RUN_DIR / f"{name}.jsonl").read_bytes()) != info["sha256"]:
            raise ValueError("Frozen cohort integrity failure")
    return manifest


def calibrate(model, manifest):
    metrics = {threshold: Metrics() for threshold in manifest["threshold_grid"]}
    for index, row in enumerate(load_rows(RUN_DIR / "calibration.jsonl").values()):
        raw = model.raw(row["text"])
        gold = [span for span in row["spans"] if span["kind"] == "PERSON"]
        for threshold, metric in metrics.items():
            metric.add(row["text"], gold, decode(row["text"], raw, threshold))
        if (index + 1) % 128 == 0:
            print(f"calibration {index + 1}/512", flush=True)
    reports = {str(threshold): metric.report() for threshold, metric in metrics.items()}
    selected = max(metrics, key=lambda threshold: (reports[str(threshold)]["exact_f1"] or 0,
                   reports[str(threshold)]["full_entity_coverage"] or 0,
                   reports[str(threshold)]["exact_precision"] or 0, threshold))
    return selected, reports


def quality(model, name, manifest, startup_ms):
    selected, calibration = calibrate(model, manifest)
    corpus = load_rows(RUN_DIR / "quality.jsonl")
    predictions, default_predictions = {}, {}
    target = RUN_DIR / f"{name}.predictions.jsonl"
    cpu_start = time.process_time()
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        for index, row in enumerate(corpus.values()):
            raw = model.raw(row["text"])
            digest = hashlib.sha256(row["text"].encode()).hexdigest()
            default = decode(row["text"], raw, 0.5)
            item = {"id": row["id"], "text_sha256": digest,
                    "spans": decode(row["text"], raw, selected), "default_spans": default}
            predictions[row["id"]] = item
            default_predictions[row["id"]] = {**item, "spans": default}
            stream.write(json.dumps(item) + "\n")
            if (index + 1) % 250 == 0:
                print(f"quality {index + 1}/{len(corpus)}", flush=True)
    calibrated = evaluate(corpus, predictions, "test", "PERSON")
    baseline = evaluate(corpus, default_predictions, "test", "PERSON")
    report = {"model": name, "backend": model.backend, "selected_threshold": selected,
              "default_threshold": 0.5, "default_threshold_note": "Common reference threshold; not each author's native default.",
              "calibration": calibration, "calibrated": calibrated, "common_threshold_0_5": baseline,
              "startup_model_load_ms": startup_ms, "quality_process_cpu_seconds": time.process_time() - cpu_start,
              "peak_process_memory_bytes": peak_memory_bytes(), "versions": versions(),
              "weights_bytes": (BASE / "models" / name / active_weights(name)).stat().st_size,
              "cohort_sha256": manifest["samples"]["quality"]["sha256"], "complete": True}
    (RUN_DIR / f"{name}.quality.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"model": name, "threshold": selected, "quality": calibrated["quality"]}), flush=True)


def timing(model, name, pass_index, startup_ms):
    report = json.loads((RUN_DIR / f"{name}.quality.json").read_text(encoding="utf-8"))
    threshold = report["selected_threshold"]
    rows = list(load_rows(RUN_DIR / "timing.jsonl").values())
    random.Random(f"{SEED}:timing-pass:{pass_index}").shuffle(rows)
    for row in list(load_rows(RUN_DIR / "calibration.jsonl").values())[:5]:
        decode(row["text"], model.raw(row["text"]), threshold)
    observations, cpu_start = [], time.process_time()
    for index, row in enumerate(rows):
        started = time.perf_counter_ns()
        spans = decode(row["text"], model.raw(row["text"]), threshold)
        elapsed = (time.perf_counter_ns() - started) / 1e6
        observations.append({"id": row["id"], "pass": pass_index, "elapsed_ms": elapsed,
                             "characters": len(row["text"]), "length_band": length_band(row["text"]),
                             "prediction_sha256": sha256(json.dumps(spans, sort_keys=True).encode())})
        if (index + 1) % 100 == 0:
            print(f"timing pass {pass_index} {index + 1}/{len(rows)}", flush=True)
    result = {"model": name, "backend": model.backend, "pass": pass_index, "observations": observations,
              "startup_model_load_ms": startup_ms, "process_cpu_seconds": time.process_time() - cpu_start,
              "peak_process_memory_bytes": peak_memory_bytes()}
    (RUN_DIR / f"{name}.timing-{pass_index}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def active_weights(name):
    if name == "gliner_multi_pii-v1":
        return "pytorch_model.bin"
    return "model_fp32.onnx" if name == "distilcamembert-base-ner" else "model.onnx"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--phase", choices=("quality", "timing", "independent"), required=True)
    parser.add_argument("--pass-index", type=int, default=0)
    args = parser.parse_args()
    manifest = verify_cohort()
    start = time.perf_counter()
    model = load_model(args.model, manifest["cpu_threads"])
    startup = (time.perf_counter() - start) * 1000
    print(f"Loaded {args.model}: {model.backend}", flush=True)
    if args.phase == "quality":
        quality(model, args.model, manifest, startup)
    elif args.phase == "timing":
        timing(model, args.model, args.pass_index, startup)
    else:
        from .independent import run

        run(model, args.model, startup)


if __name__ == "__main__":
    main()
