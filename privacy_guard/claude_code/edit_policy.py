"""Route placeholder-based document edits through the supported Write cycle.

Interface: before_edit(payload) -> HookResult. Inspect arguments only; never
open a document, consult a vault, change arguments or grant tool permission.
"""

from __future__ import annotations

from pathlib import PureWindowsPath

from privacy_guard.claude_code.responses import HookResult, allow, deny
from privacy_guard.core.tokens import PLACEHOLDER_PATTERN

_DOCUMENTS = frozenset({".txt", ".md", ".markdown", ".csv"})
_WRITE_GUIDANCE = (
    "Privacy Guard: Edit with privacy placeholders is unsupported for this local document. "
    "Read the complete file, apply the intended change using session tokens, and use Write. "
    "Normal tool permissions still apply."
)


def before_edit(payload: dict) -> HookResult:
    """Refuse an exact-string edit that uses placeholders in a supported document."""
    arguments = payload.get("tool_input")
    if payload.get("tool_name") != "Edit" or not isinstance(arguments, dict):
        return allow()
    path = arguments.get("file_path")
    if not isinstance(path, str) or PureWindowsPath(path).suffix.lower() not in _DOCUMENTS:
        return allow()
    if any(isinstance(value, str) and PLACEHOLDER_PATTERN.search(value)
           for value in (arguments.get("old_string"), arguments.get("new_string"))):
        return deny(_WRITE_GUIDANCE)
    return allow()
