"""Local journal of protection events.

Rule (PRD §20): the journal never contains inspected content, only the kind of
event. A leaked journal must reveal nothing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

DEFAULT_JOURNAL_FILE = Path.home() / ".privacy-guard" / "logs" / "guard.log"


class EventJournal:
    """Appends timestamped events to a text file, one line per event."""

    def __init__(self, path: Path = DEFAULT_JOURNAL_FILE) -> None:
        self._path = path

    def record(self, event: str, tool: str) -> None:
        """Records that a tool triggered an event. Never receives content."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as journal:
            journal.write(f"{_utc_now()}\t{event}\t{tool}\n")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
