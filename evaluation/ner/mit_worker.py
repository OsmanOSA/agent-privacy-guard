"""Reuse the frozen scoring and timing protocol for one additional MIT deployment."""

import argparse
import json
import time

from . import additional_worker
from .additional_cohort import RUN as SOURCE
from .fetch import BASE
from .mit_adapters import load_model
from .worker import calibrate, verify_cohort

RUN = BASE / "results" / "mit-comparison-20261006"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--phase", choices=("quality", "timing"), required=True)
    parser.add_argument("--pass-index", type=int, default=0)
    parser.add_argument("--resume-quality", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()
    if args.model == "distilcamembert-base-ner":
        from .adapters import load_model as load_reference

        model = load_reference(args.model)
    else:
        model = load_model(args.model)
    startup_ms = (time.perf_counter() - started) * 1000
    manifest = json.loads((SOURCE / "cohort.json").read_text(encoding="utf-8"))
    additional_worker.RUN = RUN
    if args.phase == "quality":
        calibration = verify_cohort()
        calibration_dir = RUN / "calibration"
        calibration_dir.mkdir(exist_ok=True)
        receipt_path = calibration_dir / f"{args.model}.quality.json"
        if args.resume_quality and receipt_path.exists():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt["calibration_sha256"] != calibration["samples"]["calibration"]["sha256"]:
                raise ValueError("Calibration inputs changed")
            from .mit_quality import quality

            quality(model, args.model, manifest, receipt, RUN, resume=True)
            return
        threshold, scores = calibrate(model, calibration)
        # The existing worker reads a prior calibrated threshold. This local
        # receipt supplies that threshold without modifying an earlier run.
        receipt = {"selected_threshold": threshold, "calibration": scores,
            "calibration_sha256": calibration["samples"]["calibration"]["sha256"],
            "startup_model_load_ms": startup_ms, "complete": True}
        receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
        additional_worker.ORIGINAL = calibration_dir
        additional_worker.quality(model, args.model, manifest)
        path = RUN / f"{args.model}.quality.json"
        result = json.loads(path.read_text(encoding="utf-8"))
        result.update(receipt)
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    else:
        additional_worker.timing(model, args.model, manifest, args.pass_index)
    print(f"Completed {args.model} {args.phase}", flush=True)


if __name__ == "__main__":
    main()
