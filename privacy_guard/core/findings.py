"""Findings: sensitive spans located in a text.

Shared by every detector (secrets today, personal data later) so their results
can be merged and pseudonymized the same way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Finding:
    """A sensitive span of a text: what it is (kind) and where it is (start, end)."""

    kind: str
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


def without_overlaps(findings: Iterable[Finding]) -> list[Finding]:
    """Keeps a single finding per region of text, ordered by position.

    When findings overlap, the one starting first wins, then the longest.
    On a full tie, the input order decides: detectors list their most specific
    rules first, so the most precise kind is kept.
    """
    # sorted() is stable, which preserves the input order on ties.
    ordered = sorted(findings,
                    key=lambda finding: (finding.start, -finding.length))
    
    kept: list[Finding] = []
    
    for finding in ordered:
        if not kept or finding.start >= kept[-1].end:
            kept.append(finding)
    return kept


def excluding(findings: Iterable[Finding],
              reserved: Iterable[Finding]) -> list[Finding]:
    """Drops every finding that overlaps a reserved span.

    Used to give one detection priority over another: e.g. a URL password
    must not be swallowed by an email-looking match around it.
    """
    reserved = list(reserved)
    return [finding for finding in findings
            if not any(_overlap(finding, other) for other in reserved)]


def _overlap(first: Finding, second: Finding) -> bool:
    return first.start < second.end and second.start < first.end
