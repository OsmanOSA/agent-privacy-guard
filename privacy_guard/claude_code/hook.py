"""Handling of a single Claude Code hook call.

Claude Code runs the hook before (PreToolUse) and after (PostToolUse) every tool,
and once when a session ends (SessionEnd).
It sends the event as JSON on stdin and reads the decision from stdout and the
exit code.

Interface: `run(stdin, stdout, stderr, journal, vaults, names) -> exit code`.

Fail-closed guarantee: if handling fails, nothing unchecked reaches the model.
The tool is blocked (before it runs) or its output is masked (after it ran).
"""

from __future__ import annotations

import json
from typing import Protocol, TextIO

from privacy_guard.claude_code.document_scope import is_document_read
from privacy_guard.claude_code.protection import protect_tool_output, restore_tool_input
from privacy_guard.claude_code.responses import (
    POST_TOOL_USE,
    PRE_TOOL_USE,
    SESSION_END,
    SESSION_START,
    HookResult,
    allow,
    block,
    replace_tool_output,
)
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore

FAILURE_MESSAGE = "Privacy Guard: internal error, action blocked for safety."
# Instant name detection for everything that is not a document.
QUICK_NAMES = HeuristicNameDetector()


class Journal(Protocol):
    """What the hook needs to record events
    (see privacy_guard.journal)."""

    def record(self, event: str, tool: str) -> None: ...


class NameService(Protocol):
    """The background service that finds names in documents (see privacy_guard.service.client)."""

    def ensure_running(self) -> None: ...

    def find_names(self, text: str) -> list: ...


def run(stdin: TextIO,
        stdout: TextIO,
        stderr: TextIO,
        journal: Journal,
        vaults: VaultStore,
        names: NameService) -> int:
    """Handles a full call (read, decide, write)
    and returns the exit code."""

    result = _handle_safely(stdin.read(), journal, vaults, names)
    stdout.write(result.stdout)
    stderr.write(result.stderr)

    return result.exit_code


def handle(payload: dict,
           journal: Journal,
           vaults: VaultStore,
           names: NameService) -> HookResult:
    """Decides what happens to an event: protect tool results, restore local tool inputs,
    warm the name service up when a session starts, forget the session's values when it ends."""
    event = payload["hook_event_name"]
    session_id = payload["session_id"]
    journal.record(event, payload.get("tool_name", "?"))

    if event == SESSION_START:
        # Load the NER model while the user writes the first prompt.
        names.ensure_running()
        return allow()
    if event == SESSION_END:
        vaults.close_session(session_id)
        return allow()

    core = PrivacyCore(vaults.session(session_id), names if is_document_read(payload) else QUICK_NAMES)
    if event == POST_TOOL_USE:
        return protect_tool_output(payload, core)
    if event == PRE_TOOL_USE:
        return restore_tool_input(payload, core)

    return allow()


def fail_closed(event: str) -> HookResult:
    """Fallback response when handling failed: never let content through."""
    if event == POST_TOOL_USE:
        # The tool already ran: replace its output with a neutral message.
        return replace_tool_output(f"[{FAILURE_MESSAGE} Output masked.]")
    return block(FAILURE_MESSAGE)


def _handle_safely(raw_payload: str,
                   journal: Journal,
                   vaults: VaultStore,
                   names: NameService) -> HookResult:
    # Most cautious assumption until the event has been read.
    event = PRE_TOOL_USE

    try:

        payload = json.loads(raw_payload)
        event = payload.get("hook_event_name", PRE_TOOL_USE)
        return handle(payload, journal, vaults, names)

    except Exception:
        # Deliberately broad: whatever the error, fail closed.
        return fail_closed(event)
