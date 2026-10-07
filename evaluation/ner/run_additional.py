"""Run the new reference study with pinned weights and transferred thresholds."""

import datetime
import argparse
import json
import os
import subprocess
import sys

from .additional_cohort import RUN
from .fetch import BASE, sha256
from .license_policy import eligible_models
from .run_comparison import machine
from .runtime_info import versions
from .worker import active_weights


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    models = [model["id"] for model in eligible_models()]
    artifacts = json.loads((BASE / "models/artifacts.json").read_text(encoding="utf-8"))
    for name in models:
        if sha256((BASE / "models" / name / active_weights(name)).read_bytes()) != artifacts[name][active_weights(name)]["sha256"]:
            raise ValueError("Model artifact integrity failure")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
           "HF_HOME": str(BASE / "models/hf-cache"), "HF_HUB_OFFLINE": "1"}
    run = {"started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "machine": machine(), "versions": versions(), "models": models,
           "batch_size": 1, "cpu_threads": 4, "timing_passes": 3, "timing_orders": [],
           "cohort_sha256": sha256((RUN / "cohort.json").read_bytes()),
           "model_artifacts": {name: artifacts[name][active_weights(name)] for name in models},
           "harness_hashes": {p.name: sha256(p.read_bytes()) for p in BASE.glob("*.py")}}
    path = RUN / "run.json"
    if args.resume:
        previous = json.loads(path.read_text(encoding="utf-8"))
        if previous["cohort_sha256"] != run["cohort_sha256"] or previous["model_artifacts"] != run["model_artifacts"]:
            raise ValueError("Cannot resume with changed inputs or weights")
        run = previous
        run["resumed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        run["execution_harness_hashes_at_resume"] = {p.name: sha256(p.read_bytes()) for p in BASE.glob("*.py")}
        run["resume_reason"] = "Verified composed combining mark offset repair; prior successful inputs passed complete coverage and never enter the repair branch. Failed model is rerun fully. Timing has not started."
        if run["timing_orders"]:
            raise ValueError("Resume is restricted to quality failure before timing")
    path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    def worker(name, phase, pass_index=0):
        subprocess.run([sys.executable, "-u", "-m", "evaluation.ner.additional_worker", "--model", name,
                        "--phase", phase, "--pass-index", str(pass_index)], env=env, check=True)
    for name in models:
        target = RUN / f"{name}.quality.json"
        if args.resume and target.exists():
            saved = json.loads(target.read_text(encoding="utf-8"))
            if not saved.get("complete"):
                raise ValueError("Incomplete saved quality report")
            print(f"Retained completed quality run: {name}", flush=True)
        else:
            worker(name, "quality")
    for index in range(3):
        order = models[index:] + models[:index]
        run["timing_orders"].append(order)
        path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
        for name in order:
            worker(name, "timing", index)
    run["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    print("Additional reference study completed", flush=True)


if __name__ == "__main__":
    main()
