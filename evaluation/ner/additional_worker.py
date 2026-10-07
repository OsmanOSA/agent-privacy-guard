"""Evaluate one deployment sequentially on three frozen reference corpora."""

import argparse
import json
import random
import time

from .adapters import load_model
from .additional_cohort import RUN, SEED, TASKS
from .cohort import RUN_DIR as ORIGINAL
from .decode import decode
from .fetch import sha256
from .runtime_info import peak_memory_bytes
from .score import evaluate, load_rows


def prediction(model, row, threshold, kind):
    spans = decode(row["text"], model.raw(row["text"]), threshold)
    return [{**span, "kind": kind} for span in spans]


def quality(model, name, manifest):
    threshold = json.loads((ORIGINAL / f"{name}.quality.json").read_text(encoding="utf-8"))["selected_threshold"]
    results = {"model": name, "backend": model.backend, "threshold": threshold, "datasets": {}}
    for dataset, kind in TASKS.items():
        path = RUN / f"{dataset}.jsonl"
        if sha256(path.read_bytes()) != manifest["datasets"][dataset]["quality_sha256"]:
            raise ValueError("Frozen reference cohort integrity failure")
        corpus, predictions = load_rows(path), {}
        with (RUN / f"{name}.{dataset}.predictions.jsonl").open("w", encoding="utf-8") as stream:
            for index, row in enumerate(corpus.values()):
                started = time.perf_counter_ns()
                spans = prediction(model, row, threshold, kind)
                item = {"id": row["id"], "text_sha256": row["text_sha256"], "spans": spans,
                        "elapsed_ms": (time.perf_counter_ns() - started) / 1e6}
                predictions[row["id"]] = item
                stream.write(json.dumps(item) + "\n")
                if (index + 1) % 250 == 0:
                    print(f"{name} {dataset} {index + 1}/{len(corpus)}", flush=True)
        by_domain = {}
        for domain in sorted({row["domain"] for row in corpus.values()}):
            subset = {key: row for key, row in corpus.items() if row["domain"] == domain}
            by_domain[domain] = evaluate(subset, {key: predictions[key] for key in subset}, "test", kind)["quality"]
        results["datasets"][dataset] = {**evaluate(corpus, predictions, "test", kind),
            "by_domain": by_domain, "cohort_sha256": sha256(path.read_bytes())}
        print(json.dumps({"model": name, "dataset": dataset,
                          "quality": results["datasets"][dataset]["quality"]}), flush=True)
    results.update(complete=True, peak_process_memory_bytes=peak_memory_bytes())
    (RUN / f"{name}.quality.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


def timing(model, name, manifest, pass_index):
    threshold = json.loads((RUN / f"{name}.quality.json").read_text(encoding="utf-8"))["threshold"]
    observations = []
    for dataset, kind in TASKS.items():
        path = RUN / f"{dataset}.timing.jsonl"
        if sha256(path.read_bytes()) != manifest["datasets"][dataset]["timing_sha256"]:
            raise ValueError("Frozen timing input integrity failure")
        rows = list(load_rows(path).values())
        random.Random(f"{SEED}:timing:{pass_index}:{dataset}").shuffle(rows)
        for row in rows[:5]:
            prediction(model, row, threshold, kind)
        for row in rows:
            started = time.perf_counter_ns()
            spans = prediction(model, row, threshold, kind)
            elapsed = (time.perf_counter_ns() - started) / 1e6
            observations.append({"id": row["id"], "dataset": dataset, "pass": pass_index,
                "characters": len(row["text"]), "elapsed_ms": elapsed,
                "prediction_sha256": sha256(json.dumps(spans, sort_keys=True).encode())})
        print(f"{name} timing pass {pass_index} {dataset}: {len(rows)} inputs", flush=True)
    result = {"model": name, "backend": model.backend, "pass": pass_index,
              "observations": observations, "peak_process_memory_bytes": peak_memory_bytes()}
    (RUN / f"{name}.timing-{pass_index}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--phase", choices=("quality", "timing"), required=True)
    parser.add_argument("--pass-index", type=int, default=0)
    args = parser.parse_args()
    manifest = json.loads((RUN / "cohort.json").read_text(encoding="utf-8"))
    model = load_model(args.model, manifest["cpu_threads"])
    if args.phase == "quality":
        quality(model, args.model, manifest)
    else:
        timing(model, args.model, manifest, args.pass_index)


if __name__ == "__main__":
    main()
