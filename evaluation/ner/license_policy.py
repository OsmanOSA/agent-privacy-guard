"""Apply the declared license eligibility policy before evaluation work."""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
PERMISSIVE_MODEL_LICENSES = {"mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "isc"}
COMMERCIAL_DATA_LICENSES = {"CC-BY-2.5", "CC-BY-4.0", "CC-BY-SA-2.0", "CC-BY-SA-4.0",
                            "CC0-1.0", "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
                            "LGPL-LR"}  # Local inference evaluation; corpus distribution has separate obligations.


def eligible_datasets():
    manifest = json.loads((BASE / "sources.json").read_text(encoding="utf-8"))
    return [dataset for dataset in manifest["datasets"]
            if dataset.get("commercial_evaluation") is True
            and dataset.get("evaluation_status") == "active"
            and dataset.get("license") in COMMERCIAL_DATA_LICENSES]


def require_eligible_corpus(records):
    allowed = {dataset["id"] for dataset in eligible_datasets()}
    if any(row.get("dataset") not in allowed for row in records):
        raise ValueError("Corpus is not approved for this commercial-purpose evaluation")


def eligible_models():
    manifest = json.loads((BASE / "candidates.json").read_text(encoding="utf-8"))
    return [model for model in manifest["models"]
            if model.get("license_from_card") in PERMISSIVE_MODEL_LICENSES
            and model.get("evaluation_eligible") is True]
