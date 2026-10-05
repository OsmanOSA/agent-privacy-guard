"""Compares what the detectors found with what the corpus says must be hidden.

A finding matches an expected value when both have the same category and their
spans overlap: the benchmark measures whether a value is hidden, not where the
detector drew its exact border.

    recall    = expected values that were hidden / expected values   (leaks avoided)
    precision = findings that were expected      / findings          (noise avoided)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from benchmark.annotation import AnnotatedDocument, Expected
from privacy_guard.core.findings import Finding
from privacy_guard.core.secret_detector import SECRET_RULES

_KIND_CATEGORIES = {
    "person_name": "name",
    "email": "email",
    "phone": "phone",
    "fr_postal_address": "address",
    "postal_address": "address",
    "birth_date": "birth_date",
    "iban": "banking",
    "payment_card": "banking",
    "card_security_code": "banking",
    "fr_social_security_number": "identifier",
    "fr_tax_number": "identifier",
    "fr_passport": "identifier",
    "fr_license_plate": "identifier",
    "fr_identity_card": "identifier",
    "fr_driving_licence": "identifier",
    "fr_siret": "identifier",
    "fr_siren": "identifier",
    **{secret_rule.kind: "secret" for secret_rule in SECRET_RULES},
}


@dataclass(frozen=True)
class Mistake:
    """A value that leaked (missed) or a span hidden for nothing (false alarm)."""

    document: str
    category: str
    value: str
    line: int


@dataclass
class CategoryScore:
    expected: int = 0
    hidden: int = 0
    found: int = 0
    justified: int = 0

    @property
    def recall(self) -> float | None:
        return self.hidden / self.expected if self.expected else None

    @property
    def precision(self) -> float | None:
        return self.justified / self.found if self.found else None


@dataclass
class Report:
    scores: dict[str, CategoryScore] = field(default_factory=lambda: defaultdict(CategoryScore))
    missed: list[Mistake] = field(default_factory=list)
    false_alarms: list[Mistake] = field(default_factory=list)

    def add(self, document: AnnotatedDocument,
            findings: list[Finding]) -> None:
        """Scores one document."""
        for expected in document.expected:
            score = self.scores[expected.category]
            score.expected += 1
            if any(_matches(finding, expected) for finding in findings):
                score.hidden += 1
            else:
                self.missed.append(_mistake(document, expected.category, expected.start, expected.end))

        for finding in findings:
            category = category_of(finding.kind)
            score = self.scores[category]
            score.found += 1
            if any(_matches(finding, expected) for expected in document.expected):
                score.justified += 1
            else:
                self.false_alarms.append(_mistake(document, category, finding.start, finding.end))


def category_of(kind: str) -> str:
    return _KIND_CATEGORIES.get(kind, kind)


def _matches(finding: Finding,
             expected: Expected) -> bool:
    return (category_of(finding.kind) == expected.category
            and finding.start < expected.end and expected.start < finding.end)


def _mistake(document: AnnotatedDocument,
             category: str,
             start: int,
             end: int) -> Mistake:
    return Mistake(document.name, category, document.text[start:end], document.text.count("\n", 0, start) + 1)
