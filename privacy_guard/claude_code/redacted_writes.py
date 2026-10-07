"""Refuse writes that would replace a real secret with its redaction marker.

Secrets reach the model as ⟦KIND:REDACTED⟧ and their value is never kept, so nothing
can restore them. An agent rewriting a .env or a settings file it read would
otherwise overwrite the user's keys with the marker, silently and for good. Any file
type is concerned, restorable or not.

Interface: before_redacted_write(payload) -> HookResult. Inspects the new content
only; never opens a file or a vault.
"""

from __future__ import annotations

from privacy_guard.claude_code.responses import HookResult, allow, deny
from privacy_guard.core.tokens import REDACTION_PATTERN

_REFUSAL = (
    "Privacy Guard: this change would write a redacted secret placeholder. The real secret "
    "is never kept, so the file would lose it. Leave the lines holding redacted secrets "
    "untouched: edit only the other lines, or ask the user to make this change."
)


def before_redacted_write(payload: dict) -> HookResult:
    """Refuse a Write, Edit, MultiEdit or NotebookEdit whose new content holds a redaction."""
    arguments = payload.get("tool_input")
    if not isinstance(arguments, dict):
        return allow()
    if any(isinstance(text, str) and REDACTION_PATTERN.search(text)
           for text in _new_content(payload.get("tool_name"), arguments)):
        return deny(_REFUSAL)
    return allow()


def _new_content(tool: object, arguments: dict):
    """The text a file tool is about to put on disk."""
    if tool == "Write":
        yield arguments.get("content")
    elif tool == "Edit":
        yield arguments.get("new_string")
    elif tool == "MultiEdit" and isinstance(arguments.get("edits"), list):
        yield from (step.get("new_string") for step in arguments["edits"] if isinstance(step, dict))
    elif tool == "NotebookEdit":
        yield arguments.get("new_source")
