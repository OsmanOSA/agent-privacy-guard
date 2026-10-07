"""Bounded name detections for exact repeated text, behind find_names(text).

One instance belongs to one loaded, fixed detector configuration. Reloading
the detector creates an empty cache. Only SHA-256 keys and immutable findings
stay in memory, never source text, restored values or session tokens. The
service serves requests sequentially; this adapter needs no concurrent access.
"""

from __future__ import annotations

from collections import OrderedDict
from hashlib import sha256

from privacy_guard.core.findings import Finding
from privacy_guard.core.name_detector import NameDetector


class CachedNameDetector:
    """Reuse successful detections without changing protection or session state."""

    def __init__(self, detector: NameDetector,
                 max_entries: int = 128, max_findings: int = 4096) -> None:
        if max_entries < 1 or max_findings < 1:
            raise ValueError("Cache limits must be positive")
        self._detector = detector
        self._max_entries = max_entries
        self._max_findings = max_findings
        self._cache: OrderedDict[bytes, tuple[Finding, ...]] = OrderedDict()
        self._finding_count = 0

    def find_names(self, text: str) -> list[Finding]:
        """Exact UTF-8 text is the key; exceptions never enter the cache."""
        key = sha256(text.encode("utf-8")).digest()
        if key in self._cache:
            self._cache.move_to_end(key)
            return list(self._cache[key])

        findings = tuple(self._detector.find_names(text))
        if len(findings) > self._max_findings:
            return list(findings)

        while (len(self._cache) >= self._max_entries
               or self._finding_count + len(findings) > self._max_findings):
            _, expired = self._cache.popitem(last=False)
            self._finding_count -= len(expired)
        self._cache[key] = findings
        self._finding_count += len(findings)
        return list(findings)
