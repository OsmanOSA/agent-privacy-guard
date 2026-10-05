"""Runs Privacy Guard on PIIMB and ranks it among the published models.

    <model-env python> -m benchmark.piimb [--per-task N] [--seed S]

--per-task samples N documents per task (the same ones for a given seed); 0 runs
the full benchmark (~25,000 documents, about an hour). Every text goes through
the NER model, as a document would. --tasks limits the run to some tasks, e.g.
mapa-eur-lex, whose 42 documents are whole legal texts and take most of the time.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

from benchmark.piimb.leaderboard import load_published
from benchmark.piimb.metrics import MaskingCounts, intersection, merge
from benchmark.piimb.scope import PRODUCT_SCOPE, scope_category
from privacy_guard.core.detector import SensitiveDataDetector
from privacy_guard.core.name_detector import CombinedNameDetector, HeuristicNameDetector, PlausibleNameFilter

EVAL_DIR = Path.home() / ".privacy-guard" / "eval" / "piimb"
DATA_FILE = EVAL_DIR / "data" / "test.jsonl"
REFERENCES = ("fastino__gliner2-privacy-filter-PII-multi", "openai__privacy-filter", "presidio__en_core_web_lg")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Privacy Guard on PIIMB")
    parser.add_argument("--per-task", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--tasks", help="comma-separated task names (default: all)")
    args = parser.parse_args()

    from privacy_guard.service.onnx_name_detector import OnnxNameDetector

    detector = SensitiveDataDetector(
        CombinedNameDetector([HeuristicNameDetector(), PlausibleNameFilter(OnnxNameDetector())])
    )
    documents = _sample(_load(DATA_FILE, args.tasks), args.per_task, args.seed)

    official: dict[str, MaskingCounts] = defaultdict(MaskingCounts)
    scope_true, scope_hidden = defaultdict(int), defaultdict(int)
    started = time.perf_counter()
    for number, document in enumerate(documents, start=1):
        _report_progress(number, len(documents), document["task_name"], started)
        predicted = merge([(f.start, f.end) for f in detector.find(document["text"])])
        true = [(e["start"], e["end"]) for e in document["entities"]]
        official[document["task_name"]].add(true, predicted, len(document["text"]))
        for entity in document["entities"]:
            category = scope_category(entity["label"])
            if category:
                scope_true[category] += entity["end"] - entity["start"]
                scope_hidden[category] += intersection([(entity["start"], entity["end"])], predicted)
    elapsed = time.perf_counter() - started

    print(f"{len(documents)} documents ({_sampling(args)}) in {elapsed:.0f} s, "
          f"{elapsed / len(documents) * 1000:.0f} ms per document\n")
    _print_official(official)
    _print_scope(scope_true, scope_hidden)
    _print_ranking(official)
    return 0


def _report_progress(number: int,
                     total: int,
                     task: str,
                     started: float) -> None:
    # On stderr, every 50 documents: long runs must show they are alive and how far they are.
    if number == 1 or number % 50 == 0:
        elapsed = time.perf_counter() - started
        print(f"  [{number}/{total}] {task}, {elapsed:.0f} s elapsed", file=sys.stderr, flush=True)


def _load(path: Path,
          tasks: str | None) -> list[dict]:
    wanted = set(tasks.split(",")) if tasks else None
    with path.open(encoding="utf-8") as file:
        documents = [json.loads(line) for line in file]
    return [d for d in documents if wanted is None or d["task_name"] in wanted]


def _sample(documents: list[dict],
            per_task: int,
            seed: int) -> list[dict]:
    by_task = defaultdict(list)
    for document in documents:
        by_task[document["task_name"]].append(document)
    if per_task <= 0:
        return documents
    generator = random.Random(seed)
    return [document for task in sorted(by_task)
            for document in generator.sample(by_task[task], min(per_task, len(by_task[task])))]


def _print_official(official: dict[str, MaskingCounts]) -> None:
    print("Official score (all 103 PIIMB labels, character-level masking)")
    print(f"  {'task':<18} {'F2':>6} {'precision':>10} {'recall':>8}")
    for task, counts in sorted(official.items()):
        print(f"  {task:<18} {counts.f2:>6.1%} {counts.precision:>10.1%} {counts.recall:>8.1%}")
    print(f"  {'AVERAGE':<18} {_average_f2(official):>6.1%}\n")


def _print_scope(scope_true: dict[str, int],
                 scope_hidden: dict[str, int]) -> None:
    print("Recall on the product scope (characters hidden, per category)")
    for category in PRODUCT_SCOPE:
        if scope_true[category]:
            print(f"  {category:<12} {scope_hidden[category] / scope_true[category]:>6.1%}")
    total = sum(scope_hidden.values()) / sum(scope_true.values())
    print(f"  {'ALL IN SCOPE':<12} {total:>6.1%}\n")


def _print_ranking(official: dict[str, MaskingCounts]) -> None:
    published = load_published(EVAL_DIR / "results")
    ours = _average_f2(official)
    ranked = sorted(published, key=lambda model: model.average_f2, reverse=True)
    rank = 1 + sum(model.average_f2 > ours for model in ranked)
    print(f"Ranking by average F2: Privacy Guard would be #{rank} of {len(ranked) + 1}")
    for model in ranked[:5] + [m for m in ranked if any(m.name.startswith(r) for r in REFERENCES)]:
        print(f"  #{ranked.index(model) + 1:<3} {model.average_f2:>6.1%}  {model.name}")
    print(f"  ->   {ours:>6.1%}  Privacy Guard (this run)")


def _average_f2(official: dict[str, MaskingCounts]) -> float:
    return sum(counts.f2 for counts in official.values()) / len(official)


def _sampling(args: argparse.Namespace) -> str:
    return "full benchmark" if args.per_task <= 0 else f"{args.per_task} per task, seed {args.seed}"


if __name__ == "__main__":
    sys.exit(main())
