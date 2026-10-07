"""Run three new models and contemporaneous DistilCamemBERT timing on frozen inputs."""

import datetime
import argparse
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys

from .additional_cohort import RUN as SOURCE, TASKS
from .fetch import BASE, sha256
from .mit_worker import RUN
from .run_comparison import machine
from .runtime_info import versions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    registry = json.loads((BASE / "mit-candidates.json").read_text(encoding="utf-8"))
    models = [item["id"] for item in registry["models"]]
    receipts = json.loads((BASE / "mit-artifacts.json").read_text(encoding="utf-8"))
    for name in models:
        for filename, receipt in receipts[name].items():
            if sha256((BASE / "models" / name / filename).read_bytes()) != receipt["sha256"]:
                raise ValueError("Pinned MIT artifact changed")
    RUN.mkdir(parents=True, exist_ok=True)
    for filename in ["cohort.json", *[f"{dataset}{suffix}.jsonl" for dataset in TASKS for suffix in ("", ".timing")]]:
        target = RUN / filename
        if target.exists() and target.read_bytes() != (SOURCE / filename).read_bytes():
            raise ValueError("Cannot replace a frozen input")
        shutil.copyfile(SOURCE / filename, target)
    reference = "distilcamembert-base-ner"
    for filename in [f"{reference}.quality.json", *[f"{reference}.{dataset}.predictions.jsonl" for dataset in TASKS]]:
        shutil.copyfile(SOURCE / filename, RUN / filename)
    baseline = BASE / "models" / reference / "model_fp32.onnx"
    original = json.loads((BASE / "summary-additional-20261006.json").read_text(encoding="utf-8"))
    if sha256(baseline.read_bytes()) != original["run"]["model_artifacts"][reference]["sha256"]:
        raise ValueError("DistilCamemBERT control weights changed")
    run = {"started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "models": models, "timing_models": [reference, *models], "machine": machine(),
        "versions": {**versions(), **{n: importlib.metadata.version(n) for n in ("spacy", "flair")}},
        "cpu_threads": 4, "batch_size": 1, "timing_passes": 3, "timing_orders": [],
        "cohort_sha256": sha256((RUN / "cohort.json").read_bytes()),
        "registry_sha256": sha256((BASE / "mit-candidates.json").read_bytes()),
        "artifacts_sha256": sha256((BASE / "mit-artifacts.json").read_bytes()),
        "reference_weights_sha256": sha256(baseline.read_bytes()),
        "harness_hashes": {p.name: sha256(p.read_bytes()) for p in BASE.glob("*.py")}}
    path = RUN / "run.json"
    if args.resume:
        previous = json.loads(path.read_text(encoding="utf-8"))
        for field in ("cohort_sha256", "registry_sha256", "artifacts_sha256", "reference_weights_sha256"):
            if previous[field] != run[field]:
                raise ValueError("Cannot resume with changed inputs or weights")
        if previous["timing_orders"]:
            raise ValueError("Resume is restricted to quality failure before timing")
        previous["execution_harness_hashes_at_resume"] = run["harness_hashes"]
        previous["resumed_at"] = run["started_at"]
        previous["resume_reason"] = "Modern native normalizer drops private-use glyphs in 13 SoDUCo inputs; no glyph omissions in retained Sequoia, Europeana or calibration. Inputs, references, weights, thresholds and logits unchanged. Failed corpus rerun in full."
        run = previous
    path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "HF_HOME": str(BASE / "models/hf-cache"), "HF_HUB_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false",
        "OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4", "OPENBLAS_NUM_THREADS": "4",
        "FLAIR_CACHE_ROOT": str(BASE / "models/flair-cache")}
    def worker(name, phase, index=0):
        subprocess.run([sys.executable, "-u", "-m", "evaluation.ner.mit_worker", "--model", name,
                        "--phase", phase, "--pass-index", str(index),
                        *(["--resume-quality"] if args.resume and phase == "quality" else [])], env=env, check=True)
    for name in models:
        report = RUN / f"{name}.quality.json"
        if args.resume and report.exists():
            if not json.loads(report.read_text(encoding="utf-8"))["complete"]:
                raise ValueError("Incomplete saved quality report")
            print(f"Retained completed quality model: {name}", flush=True)
        else:
            worker(name, "quality")
    for index in range(3):
        order = run["timing_models"][index:] + run["timing_models"][:index]
        run["timing_orders"].append(order)
        path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
        for name in order:
            worker(name, "timing", index)
    run["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    print("MIT model comparison completed", flush=True)


if __name__ == "__main__":
    main()
