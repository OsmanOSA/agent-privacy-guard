"""Measures detection quality on the annotated corpus (PRD §23).

    python -m benchmark                 (heuristic name detection only)
    <model-env python> -m benchmark     (adds the NER model on documents, as the service does)

Detection runs exactly as in the hook: the same SensitiveDataDetector, and the
NER model only on document files. Use --spaced when the output is read through
Privacy Guard itself (inside a protected agent session): values are printed
with separators, otherwise the protection would hide the very mistakes to study.
The corpus is fictitious, so printing its values is harmless.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path, PurePath

from benchmark.annotation import load_corpus
from benchmark.scoring import Mistake, Report
from privacy_guard.claude_code.document_scope import DOCUMENT_EXTENSIONS
from privacy_guard.core.detector import SensitiveDataDetector
from privacy_guard.core.name_detector import CombinedNameDetector, HeuristicNameDetector

CORPUS = Path(__file__).resolve().parent / "corpus"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Detection quality benchmark")
    parser.add_argument("--spaced", action="store_true", help="print values with separators")
    args = parser.parse_args()

    quick = SensitiveDataDetector(HeuristicNameDetector())
    documents_detector, model_label = _documents_detector()
    report = Report()
    started = time.perf_counter()
    for document in load_corpus(CORPUS):
        is_document = PurePath(document.name).suffix.lower() in DOCUMENT_EXTENSIONS
        detector = documents_detector if is_document else quick
        report.add(document, detector.find(document.text))
    elapsed = time.perf_counter() - started

    print(f"Name detection on documents: {model_label}  |  corpus run in {elapsed:.1f} s\n")
    _print_scores(report)
    _print_mistakes("Missed (leaks)", report.missed, args.spaced)
    _print_mistakes("False alarms (noise)", report.false_alarms, args.spaced)
    return 0


def _documents_detector() -> tuple[SensitiveDataDetector, str]:
    heuristic = HeuristicNameDetector()
    try:
        from privacy_guard.service.distil_name_detector import DistilNameDetector

        names = CombinedNameDetector([heuristic, DistilNameDetector()])
        return SensitiveDataDetector(names), "heuristic + DistilCamemBERT FP32"
    except Exception as error:
        return SensitiveDataDetector(heuristic), f"heuristic only (model unavailable: {type(error).__name__})"


def _print_scores(report: Report) -> None:
    print(f"{'category':<12} {'expected':>8} {'recall':>8} {'found':>7} {'precision':>10}")
    for category, score in sorted(report.scores.items()):
        print(f"{category:<12} {score.expected:>8} {_percent(score.recall):>8} {score.found:>7} {_percent(score.precision):>10}")


def _print_mistakes(title: str,
                    mistakes: list[Mistake],
                    spaced: bool) -> None:
    print(f"\n{title}: {len(mistakes)}")
    for mistake in mistakes:
        value = mistake.value.replace("\n", "\\n")
        print(f"  {mistake.document}:{mistake.line:<4} {mistake.category:<11} {'·'.join(value) if spaced else value}")


def _percent(ratio: float | None) -> str:
    return "-" if ratio is None else f"{ratio:.0%}"


if __name__ == "__main__":
    sys.exit(main())
