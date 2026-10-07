"""Route placeholder-based edits of restorable files through the supported Write cycle.

Interface: before_edit(payload) -> HookResult. Inspect arguments only; never
open a document, consult a vault, change arguments or grant tool permission.

An exact-string Edit cannot work on tokens: placeholders in old_string are absent
from the file on disk, and placeholders in new_string would land there unrestored.
A complete Write of the file gets its values back (core/restorable_files.py).
"""

from __future__ import annotations

from privacy_guard.claude_code.responses import HookResult, allow, deny
from privacy_guard.core.restorable_files import is_restorable
from privacy_guard.core.tokens import PLACEHOLDER_PATTERN

_EDIT_TOOLS = frozenset({"Edit", "MultiEdit"})
_WRITE_GUIDANCE = (
    "Privacy Guard: Edit with privacy placeholders is unsupported for this local file. "
    "Read the complete file, apply the intended change using session tokens, and use Write. "
    "Normal tool permissions still apply."
)


def before_edit(payload: dict) -> HookResult:
    """Refuse an exact-string edit that uses placeholders in a restorable file."""
    arguments = payload.get("tool_input")
    if payload.get("tool_name") not in _EDIT_TOOLS or not isinstance(arguments, dict):
        return allow()
    path = arguments.get("file_path")
    if not isinstance(path, str) or not is_restorable(path):
        return allow()
    if any(isinstance(value, str) and PLACEHOLDER_PATTERN.search(value) for value in _edit_strings(arguments)):
        return deny(_WRITE_GUIDANCE)
    return allow()


def _edit_strings(arguments: dict):
    """old_string and new_string of an Edit, or of each MultiEdit step."""
    edits = arguments.get("edits")
    steps = [step for step in edits if isinstance(step, dict)] if isinstance(edits, list) else [arguments]
    for step in steps:
        yield step.get("old_string")
        yield step.get("new_string")
