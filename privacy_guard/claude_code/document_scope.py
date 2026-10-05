"""Which tool results are documents, worth the NER model.

The model finds names in free text (CVs, letters, contracts) but is slow on
large inputs and mistakes code identifiers for people ("Claude Code"). It is
therefore kept for reads of document files; every other output relies on the
instant detectors.
"""

from __future__ import annotations

import re
from pathlib import PurePath

DOCUMENT_EXTENSIONS = frozenset(
    {".txt", ".md", ".markdown", ".rst", ".csv", ".tsv", ".rtf", ".html", ".htm",
     ".eml", ".msg", ".pdf", ".doc", ".docx", ".odt"}
)
# A shell command that names a document file: cat cv.txt, head notes.md, ...
_DOCUMENT_IN_COMMAND = re.compile(
    r"\.(?:" + "|".join(extension[1:] for extension in DOCUMENT_EXTENSIONS) + r")\b", re.IGNORECASE
)


def is_document_read(payload: dict) -> bool:
    """Tells whether a tool event reads a document file."""
    tool_input = payload.get("tool_input") or {}
    if payload.get("tool_name") == "Read":
        return PurePath(tool_input.get("file_path", "")).suffix.lower() in DOCUMENT_EXTENSIONS
    if payload.get("tool_name") == "Bash":
        return _DOCUMENT_IN_COMMAND.search(tool_input.get("command", "")) is not None
    return False
