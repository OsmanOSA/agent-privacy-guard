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
     ".eml", ".msg", ".pdf", ".doc", ".docx", ".odt",
     # Logs and Claude Code's background-command output files carry free text that
     # mentions people (benchmark: traceback.log; boundary scenario background-command).
     ".log", ".output",
     # SQL dumps and seeds hold free-text columns (notes, comments) that name people
     # (benchmark: seed.sql).
     ".sql"}
)
# A shell command that names a document file: cat cv.txt, head notes.md, ...
_DOCUMENT_IN_COMMAND = re.compile(
    r"\.(?:" + "|".join(extension[1:] for extension in DOCUMENT_EXTENSIONS) + r")\b", re.IGNORECASE
)
# A Grep output line from a document: notes.md:3:..., C:\docs\cv.txt-4-... (context line).
_DOCUMENT_LINE = re.compile(
    r"^(?:[A-Za-z]:)?[^\n:]*\.(?:" + "|".join(extension[1:] for extension in DOCUMENT_EXTENSIONS) + r")[:-]",
    re.IGNORECASE | re.MULTILINE,
)
# ripgrep file types that select documents (Grep's `type` argument).
_DOCUMENT_TYPES = frozenset(extension[1:] for extension in DOCUMENT_EXTENSIONS)


def is_document_read(payload: dict) -> bool:
    """Tells whether a tool event reads a document file."""
    tool_input = payload.get("tool_input") or {}
    if payload.get("tool_name") == "Read":
        return PurePath(tool_input.get("file_path", "")).suffix.lower() in DOCUMENT_EXTENSIONS
    if payload.get("tool_name") == "Bash":
        return _DOCUMENT_IN_COMMAND.search(tool_input.get("command", "")) is not None
    if payload.get("tool_name") == "PowerShell":  # Get-Content notes.md, type cv.txt, ...
        return _DOCUMENT_IN_COMMAND.search(tool_input.get("command", "")) is not None
    if payload.get("tool_name") == "Grep":
        return _searches_documents(tool_input, payload.get("tool_response"))
    # MCP servers return records from external systems (CRM, tickets, mail): names
    # there are data, as in a document (boundary scenario mcp-result).
    tool = payload.get("tool_name")
    return isinstance(tool, str) and tool.startswith("mcp__")


def _searches_documents(tool_input: dict, response: object) -> bool:
    """Grep prints matched lines, often of documents: its target or line prefixes tell."""
    targets = (tool_input.get("path"), tool_input.get("glob"))
    if any(isinstance(target, str) and _DOCUMENT_IN_COMMAND.search(target) for target in targets):
        return True
    if tool_input.get("type") in _DOCUMENT_TYPES:
        return True
    # Claude Code leaves `filenames` empty in content mode; each line starts with its file.
    content = response.get("content") if isinstance(response, dict) else None
    return isinstance(content, str) and _DOCUMENT_LINE.search(content) is not None
