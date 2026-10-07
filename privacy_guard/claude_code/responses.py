"""Hook responses, in the exact shape Claude Code expects.

Every way the hook can answer is built here, so the protocol details
(exit codes, JSON field names) live in a single place.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

PRE_TOOL_USE = "PreToolUse"
POST_TOOL_USE = "PostToolUse"
POST_TOOL_USE_FAILURE = "PostToolUseFailure"
SESSION_START = "SessionStart"
SESSION_END = "SessionEnd"

# Exit codes as interpreted by Claude Code.
EXIT_ALLOW = 0
EXIT_BLOCK = 2  # blocks the tool and shows stderr to the model


@dataclass(frozen=True)
class HookResult:
    """The hook's response: exit code plus what to write on stdout and stderr."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""


def allow() -> HookResult:
    """Lets the tool call go on unchanged."""
    return HookResult(EXIT_ALLOW)


def block(message: str) -> HookResult:
    """Stops the tool before it runs; the message is shown to the model."""
    return HookResult(EXIT_BLOCK, stderr=message)


def stop(message: str, **fields: object) -> HookResult:
    """Stop further processing, including after a tool has already completed."""
    response = {**fields, "continue": False, "stopReason": message, "systemMessage": message}
    return HookResult(EXIT_ALLOW, stdout=json.dumps(response, ensure_ascii=False))


def replace_tool_input(tool_input: dict) -> HookResult:
    """Runs the tool with new arguments.

    No permissionDecision on purpose: Claude Code's normal permission flow
    still applies, so the user keeps approving tools as before.
    """
    return _specific_output(PRE_TOOL_USE, updatedInput=tool_input)


def replace_tool_output(tool_output: object) -> HookResult:
    """Shows the model a different tool result. Must keep the original shape."""
    return _specific_output(POST_TOOL_USE, updatedToolOutput=tool_output)


def _specific_output(event: str,
                     **fields: object) -> HookResult:
    response = {"hookSpecificOutput": {"hookEventName": event, **fields}}
    return HookResult(EXIT_ALLOW, stdout=json.dumps(response, ensure_ascii=False))
