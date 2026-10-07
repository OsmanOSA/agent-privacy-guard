"""Compare CPU window batches on frozen real inputs; no cache or deployment."""

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from evaluation.ner.additional_cohort import RAW, RUN, TASKS
from evaluation.ner.process_memory import process_memory
from evaluation.ner.window_batch import WindowBatchModel
from privacy_guard.service.distil_files import DEFAULT_DISTIL_DIR, MANIFEST, REVISION
from privacy_guard.service.model_files import ModelFiles
from privacy_guard.service.ner_spans import decode
from privacy_guard.service.ner_tokens import TokenModel


def digest(content):
    return hashlib.sha256(content).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def excerpts():
    reference = json.loads((PROJECT / "evaluation/ner/latency-length-20261006.json").read_text())
    source = RAW / "europeana.bio"
    assert digest(source.read_bytes()) == reference["source_sha256"]
    text = " ".join(line.rsplit(None, 1)[0] for line in source.read_text(encoding="utf-8").splitlines() if line.strip())
    result = []
    for case in reference["cases"]:
        selected = text[:case["characters"]]
        assert digest(selected.encode()) == case["text_sha256"]
        result.append((case, selected))
    return result


def infer(model, text):
    return decode(text, model.raw(text), threshold=0.5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-batch", type=int, choices=[1, 2, 4])
    args = parser.parse_args()
    assert ModelFiles(DEFAULT_DISTIL_DIR, MANIFEST).is_ready()
    cases = excerpts()
    if args.memory_batch:
        model = WindowBatchModel(DEFAULT_DISTIL_DIR, args.memory_batch)
        loaded = process_memory()
        infer(model, cases[-1][1])
        print(json.dumps({"batch_size": args.memory_batch, "after_load": loaded,
                          "after_long_inference": process_memory()}))
        return
    model = WindowBatchModel(DEFAULT_DISTIL_DIR, 1)
    baseline = TokenModel(DEFAULT_DISTIL_DIR, threads=4)
    checked, drift = {}, []
    for corpus in TASKS:
        predictions = {row["id"]: row for row in rows(RUN / f"distilcamembert-base-ner.{corpus}.predictions.jsonl")}
        cohort = rows(RUN / f"{corpus}.timing.jsonl")[:12]
        for row in cohort:
            expected = predictions[row["id"]]
            assert digest(row["text"].encode()) == expected["text_sha256"]
            for size in (1, 2, 4):
                model.batch_size = size
                actual = [{**span, "kind": TASKS[corpus]} for span in infer(model, row["text"])]
                if actual != expected["spans"]:
                    drift.append({"corpus": corpus, "id": row["id"], "batch_size": size})
        checked[corpus] = len(cohort)
    long_reference = []
    for case, text in cases:
        expected = infer(baseline, text)
        long_reference.append(expected)
        for size in (1, 2, 4):
            model.batch_size = size
            if infer(model, text) != expected:
                drift.append({"excerpt_tokens": case["tokens"], "batch_size": size})
    del baseline
    print(json.dumps({"stage": "reference checks", "inputs": checked, "prediction_drift": len(drift)}), flush=True)
    measurements = []
    # Counterbalance configuration order across three passes on one loaded session.
    orders = [(1, 2, 4), (2, 4, 1), (4, 1, 2)]
    for index, (case, text) in enumerate(cases):
        elapsed = {size: [] for size in (1, 2, 4)}
        for order in orders:
            for size in order:
                model.batch_size = size
                start = time.perf_counter()
                actual = infer(model, text)
                elapsed[size].append((time.perf_counter() - start) * 1000)
                if actual != long_reference[index]:
                    drift.append({"excerpt_tokens": case["tokens"], "batch_size": size, "phase": "timing"})
        record = {"tokens": case["tokens"], "windows": case["windows"], "text_sha256": case["text_sha256"],
                  "latency": {str(size): {"elapsed_ms": values, "median_ms": statistics.median(values)}
                              for size, values in elapsed.items()}}
        measurements.append(record)
        print(json.dumps({"tokens": case["tokens"], "medians_ms": {s: round(v["median_ms"], 1) for s, v in record["latency"].items()}}), flush=True)
    memory = []
    for size in (1, 2, 4):
        completed = subprocess.run([sys.executable, __file__, "--memory-batch", str(size)],
                                   capture_output=True, text=True, timeout=60, check=True)
        memory.append(json.loads(completed.stdout))
    report = {"date": "2026-10-06", "revision": REVISION, "platform": platform.platform(),
              "threads": 4, "provider": "CPUExecutionProvider", "variant": "onnx-fp32",
              "threshold": 0.5, "window_tokens": 512, "window_overlap": 64,
              "checked_real_corpus_inputs": checked, "prediction_drift_count": len(drift), "prediction_drift": drift,
              "latency_cases": measurements, "isolated_worker_memory": memory,
              "passes": 3, "configuration_orders": orders,
              "scope": "Loaded model tokenization, window inference and decoding; no detection cache, hook, IPC or vault",
              "limitations": "Single machine and published source for timing; three observations per configuration; system load uncontrolled. Memory is fresh-process peak working set, not model-only memory.",
              "model_sha256": MANIFEST["model.onnx"], "tokenizer_sha256": MANIFEST["tokenizer.json"],
              "harness_sha256": {name: digest((PROJECT / name).read_bytes()) for name in (
                  "tools/check_window_batches.py", "evaluation/ner/window_batch.py", "privacy_guard/service/ner_tokens.py")}}
    path = PROJECT / "evaluation/ner/window-batches-20261006.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": path.name, "prediction_drift": len(drift),
                      "peak_memory_mib": {m["batch_size"]: round(m["after_long_inference"]["peak_working_set_bytes"] / 2**20, 1) for m in memory}}))


if __name__ == "__main__":
    main()
