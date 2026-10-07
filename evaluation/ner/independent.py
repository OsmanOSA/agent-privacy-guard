"""Score FENEC documents using the WikiNER calibration, without retuning."""

import hashlib
import json
import time

from .cohort import RUN_DIR
from .decode import decode
from .fetch import sha256
from .metrics import Metrics
from .runtime_info import peak_memory_bytes
from .score import evaluate, load_rows


def run(model, name, startup_ms):
    manifest = json.loads((RUN_DIR / "independent-cohort.json").read_text(encoding="utf-8"))
    path = RUN_DIR / "independent.jsonl"
    if sha256(path.read_bytes()) != manifest["sha256"]:
        raise ValueError("Independent corpus integrity failure")
    threshold = json.loads((RUN_DIR / f"{name}.quality.json").read_text(encoding="utf-8"))["selected_threshold"]
    corpus, predictions, observations = load_rows(path), {}, []
    individual = Metrics()
    for row in corpus.values():
        started = time.perf_counter_ns()
        spans = decode(row["text"], model.raw(row["text"]), threshold)
        elapsed = (time.perf_counter_ns() - started) / 1e6
        predictions[row["id"]] = {"id": row["id"], "text_sha256": hashlib.sha256(row["text"].encode()).hexdigest(), "spans": spans}
        individual.add(row["text"], [s for s in row["spans"] if s["source_label"] == "pers.ind"], spans)
        observations.append({"id": row["id"], "characters": len(row["text"]), "elapsed_ms": elapsed})
        print(f"independent {len(predictions)}/{len(corpus)}", flush=True)
    by_dataset = {}
    for dataset in sorted({r["dataset"] for r in corpus.values()}):
        selected = {key: row for key, row in corpus.items() if row["dataset"] == dataset}
        by_dataset[dataset] = evaluate(selected, {key: predictions[key] for key in selected}, "test", "PERSON")
    report = {"model": name, "backend": model.backend, "selected_threshold": threshold,
              "quality": evaluate(corpus, predictions, "test", "PERSON")["quality"],
              "by_dataset": by_dataset, "individual_person_only": individual.report(),
              "single_pass_document_observations": observations, "startup_model_load_ms": startup_ms,
              "peak_process_memory_bytes": peak_memory_bytes(), "cohort_sha256": manifest["sha256"], "complete": True}
    (RUN_DIR / f"{name}.independent.predictions.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in predictions.values()), encoding="utf-8")
    (RUN_DIR / f"{name}.independent.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"model": name, "independent_quality": report["quality"]}), flush=True)
