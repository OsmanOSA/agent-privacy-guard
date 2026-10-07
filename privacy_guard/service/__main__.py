"""Entry point of the background service: `python -m privacy_guard.service --run-dir DIR`.

Started by the hook (see client.py), never by hand. Runs with the Python of the
model environment when it is installed, so the NER model can be imported.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from privacy_guard.core.name_detector import (
    CombinedNameDetector,
    NameDetector,
)
from privacy_guard.core.insee_names import local_name_detector
from privacy_guard.service.channel import DEFAULT_RUN_DIR, ServiceChannel
from privacy_guard.service.distil_files import DEFAULT_DISTIL_DIR, DISTIL_DIRECTORY
from privacy_guard.service.ner_policy import requires_model
from privacy_guard.service.server import serve

# Release model memory after an hour without requests. SessionStart warms it up.
IDLE_SECONDS = 3600
LOG_FILE = "service.log"


def main() -> None:
    # The service has no console. On Windows its output would then default to
    # cp1252, and any non-ASCII message from a library would crash the service.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(prog="privacy_guard.service")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    args = parser.parse_args()

    log_file = args.run_dir.parent / "logs" / LOG_FILE
    model_dir = args.run_dir.parent / "models" / DISTIL_DIRECTORY
    serve(ServiceChannel(args.run_dir),
          lambda: _load_detector(log_file, model_dir, requires_model(args.run_dir.parent)), IDLE_SECONDS)


def _load_detector(log_file: Path, model_dir: Path = DEFAULT_DISTIL_DIR,
                   required: bool = False) -> NameDetector:
    """The heuristic, combined with the NER model when it is installed."""
    heuristic = local_name_detector(model_dir.parent.parent)
    if not required and not model_dir.exists():
        _log(log_file, "DistilCamemBERT not installed: names found by the heuristic only")
        return heuristic
    try:
        from privacy_guard.service.distil_name_detector import DistilNameDetector

        detector = CombinedNameDetector([heuristic, DistilNameDetector(model_dir)])
    except Exception as error:
        _log(log_file, f"Installed DistilCamemBERT unavailable ({type(error).__name__}): document detection blocked")
        raise
    _log(log_file, "DistilCamemBERT FP32 loaded; threshold=0.5; CPU threads=4")
    return detector


def _log(log_file: Path,
         message: str) -> None:
    # Service state only, never content (PRD §20).
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as log:
        log.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\t{message}\n")


if __name__ == "__main__":
    main()
