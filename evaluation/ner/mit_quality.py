"""Resume only complete, fingerprint-validated per-corpus quality outputs."""

import json
import time

from .additional_cohort import TASKS
from .additional_worker import prediction
from .fetch import sha256
from .runtime_info import peak_memory_bytes
from .score import evaluate, load_rows


def quality(model, name, manifest, receipt, run, resume=False):
    threshold = receipt["selected_threshold"]
    result = {"model": name, "backend": model.backend, "threshold": threshold, "datasets": {}}
    for dataset, kind in TASKS.items():
        path = run / f"{dataset}.jsonl"
        if sha256(path.read_bytes()) != manifest["datasets"][dataset]["quality_sha256"]:
            raise ValueError("Frozen reference integrity failure")
        corpus = load_rows(path)
        target = run / f"{name}.{dataset}.predictions.jsonl"
        saved = load_rows(target) if resume and target.exists() else {}
        if saved.keys() == corpus.keys():
            evaluate(corpus, saved, "test", kind)
            predictions = saved
            print(f"Retained complete validated predictions: {name} {dataset}", flush=True)
        else:
            predictions = {}
            with target.open("w", encoding="utf-8") as stream:
                for index, row in enumerate(corpus.values()):
                    start = time.perf_counter_ns()
                    spans = prediction(model, row, threshold, kind)
                    item = {"id": row["id"], "text_sha256": row["text_sha256"], "spans": spans,
                        "elapsed_ms": (time.perf_counter_ns() - start) / 1e6}
                    predictions[row["id"]] = item
                    stream.write(json.dumps(item) + "\n")
                    if (index + 1) % 250 == 0:
                        print(f"{name} {dataset} {index + 1}/{len(corpus)}", flush=True)
        domains = {}
        for domain in sorted({row["domain"] for row in corpus.values()}):
            subset = {key: row for key, row in corpus.items() if row["domain"] == domain}
            domains[domain] = evaluate(subset, {key: predictions[key] for key in subset}, "test", kind)["quality"]
        result["datasets"][dataset] = {**evaluate(corpus, predictions, "test", kind), "by_domain": domains,
            "cohort_sha256": sha256(path.read_bytes())}
        print(json.dumps({"model": name, "dataset": dataset,
            "quality": result["datasets"][dataset]["quality"]}), flush=True)
    result.update(receipt, complete=True, peak_process_memory_bytes=peak_memory_bytes())
    (run / f"{name}.quality.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
