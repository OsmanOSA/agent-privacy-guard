"""The published PIIMB results (dataset piimb/pii-masking-benchmark-results), cached locally.

Each model has one JSON file per task holding its masking F2; a model's rank
score is the simple average of its task scores, as on the official leaderboard.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

RESULTS_API = "https://huggingface.co/api/datasets/piimb/pii-masking-benchmark-results/tree/main/results"
RESULTS_FILES = "https://huggingface.co/datasets/piimb/pii-masking-benchmark-results/resolve/main/results"
TIMEOUT_SECONDS = 30
# Next to its task results, each model folder describes the model itself.
METADATA_FILE = "model_meta"


@dataclass(frozen=True)
class PublishedModel:
    name: str
    f2_by_task: dict[str, float]

    @property
    def average_f2(self) -> float:
        return sum(self.f2_by_task.values()) / len(self.f2_by_task)


def load_published(cache: Path) -> list[PublishedModel]:
    """Every published model, downloading its result files the first time."""
    cache.mkdir(parents=True, exist_ok=True)
    models = []
    for folder in _json(RESULTS_API):
        name = folder["path"].split("/")[-1]
        scores = {}
        for entry in _json(f"{RESULTS_API}/{name}"):
            task = Path(entry["path"]).stem
            if task == METADATA_FILE:
                continue
            result = _cached(cache / name / f"{task}.json", f"{RESULTS_FILES}/{name}/{task}.json")
            scores[task] = result["scores"]["test"][0]["f2"]
        models.append(PublishedModel(name, scores))
    return models


def _cached(path: Path,
            url: str) -> dict:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_download(url))
    return json.loads(path.read_text(encoding="utf-8"))


def _json(url: str) -> list:
    return json.loads(_download(url))


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        return response.read()
