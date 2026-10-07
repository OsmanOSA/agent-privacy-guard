"""The heuristic standing in for a document model that could not load.

Founder's choice (2026-10-07, V1 readiness item 06): when the installed model fails
to load (memory, damaged files), document reads continue with the heuristic instead
of being masked whole, and every document result says that detection is reduced.
The heuristic misses about half of the names, so the warning must reach the user even
when nothing was found.

Interface: ReducedNameDetector(detector, reason).find_names(text) / .reduced
`reason` is one of protection_summary.REDUCED_REASONS, never an exception text.
"""

from __future__ import annotations

from privacy_guard.core.findings import Finding
from privacy_guard.core.name_detector import NameDetector
from privacy_guard.protection_summary import REDUCED_REASONS


class ReducedNameDetector:
    """Answers with the heuristic and states why detection is reduced."""

    def __init__(self, detector: NameDetector, reason: str) -> None:
        if reason not in REDUCED_REASONS:
            raise ValueError("Unknown reduced-detection reason")
        self._detector = detector
        self.reduced = reason

    def find_names(self, text: str) -> list[Finding]:
        return self._detector.find_names(text)
