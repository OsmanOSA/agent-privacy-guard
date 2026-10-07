"""Explain token-based document edits when a protected Read reaches Claude.

Interface: guide_document_read(payload, protected_output, result) -> HookResult.
Add content-free guidance before Edit validation; never inspect or modify disk.
"""

from __future__ import annotations

import json
from privacy_guard.claude_code.responses import POST_TOOL_USE, HookResult
from privacy_guard.core.restorable_files import is_restorable
from privacy_guard.core.tokens import PLACEHOLDER_PATTERN

_GUIDANCE = (
    "Privacy Guard: for changes spanning privacy placeholders, use Write with session tokens. "
    "Before rewriting, read the complete file and preserve unrelated content. "
    "Do not use Edit to match placeholders against original disk values. "
    "Plain amount or status edits may use Edit. Normal tool permissions still apply."
)


def guide_document_read(payload: dict, protected: object, result: HookResult) -> HookResult:
    """Attach Write guidance to protected document reads and unchanged-file results."""
    arguments = payload.get("tool_input")
    if (payload.get("hook_event_name") != POST_TOOL_USE or payload.get("tool_name") != "Read"
            or not isinstance(arguments, dict) or not isinstance(arguments.get("file_path"), str)
            or not is_restorable(arguments["file_path"])):
        return result
    cached = isinstance(protected, dict) and protected.get("type") == "file_unchanged"
    if not cached and not _has_placeholders(protected):
        return result
    response = json.loads(result.stdout) if result.stdout else {"hookSpecificOutput": {"hookEventName": POST_TOOL_USE}}
    response["hookSpecificOutput"]["additionalContext"] = _GUIDANCE
    return HookResult(result.exit_code, json.dumps(response, ensure_ascii=False), result.stderr)


def _has_placeholders(value: object) -> bool:
    if isinstance(value, str):
        return PLACEHOLDER_PATTERN.search(value) is not None
    if isinstance(value, (list, dict)):
        return any(_has_placeholders(item) for item in (value.values() if isinstance(value, dict) else value))
    return False
