"""PIIMB's masking metrics, reproduced exactly from its src/piimb/metrics.py (v0.3.0).

Character-level and label-agnostic: overlapping spans are merged, then
    precision = predicted characters inside true PII / predicted characters
    recall    = true PII characters covered by a prediction / true PII characters
    F2 weighs recall twice as much as precision: a leak costs more than over-masking.
Numerators and denominators are summed over all documents of a task before dividing.
"""

from __future__ import annotations

from dataclasses import dataclass

Span = tuple[int, int]


@dataclass
class MaskingCounts:
    """Running character counts over a task; the ratios are derived at the end."""

    predicted: int = 0
    true: int = 0
    intersection: int = 0
    text: int = 0

    def add(self, true_spans: list[Span],
            predicted_spans: list[Span],
            text_length: int) -> None:
        true, predicted = merge(true_spans), merge(predicted_spans)
        self.true += length(true)
        self.predicted += length(predicted)
        self.intersection += intersection(predicted, true)
        self.text += text_length

    @property
    def precision(self) -> float:
        return self.intersection / self.predicted if self.predicted else 0.0

    @property
    def recall(self) -> float:
        return self.intersection / self.true if self.true else 0.0

    @property
    def f2(self) -> float:
        return f_beta(self.precision, self.recall, beta=2)


def merge(spans: list[Span]) -> list[Span]:
    """Merges overlapping spans into non-overlapping, sorted ones."""
    merged: list[Span] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def length(spans: list[Span]) -> int:
    return sum(end - start for start, end in spans)


def intersection(spans_a: list[Span],
                 spans_b: list[Span]) -> int:
    return sum(max(0, min(a_end, b_end) - max(a_start, b_start))
               for a_start, a_end in spans_a for b_start, b_end in spans_b)


def f_beta(precision: float,
           recall: float,
           beta: float) -> float:
    if precision + recall == 0:
        return 0.0
    return (1 + beta ** 2) * precision * recall / (beta ** 2 * precision + recall)
