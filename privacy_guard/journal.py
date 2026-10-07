"""Local journal of protection events.

Event records contain only metadata. The separate protection summary journal
includes occurrence counts and document basenames by the user's request, never
inspected body text, values, full paths or token identifiers.
"""

from __future__ import annotations

import json

from datetime import datetime, timezone
from pathlib import Path

from privacy_guard.protection_summary import ProtectionSummary
from privacy_guard.diagnostics import CATEGORIES, EVENTS, STAGES, TOOLS, fixed

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

    def record_protection(self, summary: ProtectionSummary) -> None:
        """Append counts and the allowed basename after successful protection."""
        path = self._path.with_name("protection.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {"timestamp": _utc_now(), **summary.record()}
        with path.open("a", encoding="utf-8") as journal:
            journal.write(json.dumps(row, ensure_ascii=False) + "\n")

    def record_failure(self, event, tool, stage, category) -> None:
        """Allowlisted codes only; no exception objects, messages or identities."""
        if isinstance(tool, str) and tool.startswith('mcp__'):
            tool = 'MCP'
        row = dict(timestamp=_utc_now(), event=fixed(event, EVENTS, 'unknown'),
                   tool=fixed(tool, TOOLS, 'unknown'), stage=fixed(stage, STAGES, 'unknown'),
                   category=fixed(category, CATEGORIES, 'unexpected'))
        path = self._path.with_name('failures.jsonl')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as journal:
            journal.write(json.dumps(row) + '\n')


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
