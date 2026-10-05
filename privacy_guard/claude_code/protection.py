"""Applies PrivacyCore to Claude Code tool events.

- After a tool ran (PostToolUse): every text in its result is protected, so the
  model only sees tokens.
- Before a tool runs (PreToolUse): tokens in its arguments are restored, so the
  machine works with the real values. Only for tools that execute locally:
  restoring for a sub-agent or a remote tool would hand the real value back to
  a model.
"""

from __future__ import annotations

from typing import Callable

from privacy_guard.claude_code.responses import HookResult, allow, replace_tool_input, replace_tool_output
from privacy_guard.core.privacy_core import PrivacyCore

# Tools whose arguments never reach a model: they run on the user's machine.
LOCAL_TOOLS = frozenset({"Bash", "Write", "Edit", "MultiEdit", "NotebookEdit"})


def protect_tool_output(payload: dict,
                        core: PrivacyCore) -> HookResult:
    """Replaces the secrets of a tool result with tokens, keeping its shape."""
    output = payload.get("tool_response")
    protected = map_strings(output, core.protect)

    return allow() if protected == output else replace_tool_output(protected)


def restore_tool_input(payload: dict,
                       core: PrivacyCore) -> HookResult:
    """Puts the real values back into the arguments of a local tool."""
    if payload.get("tool_name") not in LOCAL_TOOLS:
        return allow()

    tool_input = payload.get("tool_input")
    restored = map_strings(tool_input, core.restore)

    return allow() if restored == tool_input else replace_tool_input(restored)


def map_strings(value: object,
                transform: Callable[[str], str]) -> object:
    """Applies `transform` to every string nested in JSON-like data, keeping the structure."""
    if isinstance(value, str):
        return transform(value)
    if isinstance(value, list):
        return [map_strings(item, transform) for item in value]
    if isinstance(value, dict):
        return {key: map_strings(item, transform) for key, item in value.items()}
    return value
