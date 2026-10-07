"""Run the frozen comparison sequentially, rotating model order for timing."""

import datetime
import json
import os
import platform
import subprocess
import sys

from .cohort import RUN_DIR
from .fetch import BASE, sha256
from .license_policy import eligible_models
from .runtime_info import versions
from .score import evaluate, load_rows
from .worker import active_weights, verify_cohort


def command(args, env):
    subprocess.run([sys.executable, "-u", "-m", "evaluation.ner.worker", *args], env=env, check=True)


def machine():
    code = "[PSCustomObject]@{CPU=(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors); RAMBytes=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory} | ConvertTo-Json -Depth 4"
    output = subprocess.check_output(["powershell", "-NoProfile", "-Command", code], text=True)
    power = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True, errors="replace")
    return {**json.loads(output), "power_scheme": power.stdout.strip() if power.returncode == 0 else None,
            "power_query_status": power.returncode, "power_query_error": power.stderr.strip(), "platform": platform.platform()}


def main():
    models = [model["id"] for model in eligible_models()]
    cohort = verify_cohort()
    artifacts = json.loads((BASE / "models/artifacts.json").read_text(encoding="utf-8"))
    for name in models:
        filename = active_weights(name)
        if sha256((BASE / "models" / name / filename).read_bytes()) != artifacts[name][filename]["sha256"]:
            raise ValueError("Active model artifact integrity failure")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
           "HF_HOME": str(BASE / "models/hf-cache"), "HF_HUB_OFFLINE": "1"}
    manifest = {"started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "machine": machine(), "versions": versions(), "batch_size": 1,
                "intra_op_threads": 4, "inter_op_threads": {"token_classifier_onnx": 1,
                    "legacy_pytorch": 1, "current_gliner2": "ORT default; sequential execution"}, "timing_passes": 3,
                "quality_model_order": models, "timing_model_orders": [],
                "notes": "Quality and independent phases finish before controlled latency; no prediction cache",
                "active_artifacts": {name: artifacts[name][active_weights(name)] for name in models},
                "cached_backbone_files": {str(p.relative_to(BASE / "models")): sha256(p.read_bytes())
                    for p in (BASE / "models/hf-cache/hub/models--microsoft--mdeberta-v3-base/snapshots").glob("*/*") if p.is_file()},
                "baseline_implementation_sha256": sha256((BASE.parents[1] / "privacy_guard/service/onnx_name_detector.py").read_bytes()),
                "harness_hashes": {p.name: sha256(p.read_bytes()) for p in BASE.glob("*.py")}}
    target = RUN_DIR / "run.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for name in models:
        if not (RUN_DIR / f"{name}.quality.json").exists():
            command(["--model", name, "--phase", "quality"], env)
        report = json.loads((RUN_DIR / f"{name}.quality.json").read_text(encoding="utf-8"))
        if not report["complete"] or report["cohort_sha256"] != cohort["samples"]["quality"]["sha256"]:
            raise ValueError("Incomplete or mismatched quality run")
        fresh = evaluate(load_rows(RUN_DIR / "quality.jsonl"), load_rows(RUN_DIR / f"{name}.predictions.jsonl"), "test", "PERSON")
        if fresh != report["calibrated"]:
            raise ValueError("Saved quality score differs from its predictions")
    for name in models:
        command(["--model", name, "--phase", "independent"], env)
    for pass_index in range(3):
        order = models[pass_index:] + models[:pass_index]
        manifest["timing_model_orders"].append(order)
        target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        for name in order:
            print(f"Controlled timing pass {pass_index}: {name}", flush=True)
            command(["--model", name, "--phase", "timing", "--pass-index", str(pass_index)], env)
    manifest["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("All models and timing passes completed", flush=True)


if __name__ == "__main__":
    main()
