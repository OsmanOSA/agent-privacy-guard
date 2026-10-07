"""Handling of a single Claude Code hook call.

Claude Code runs the hook before (PreToolUse) and after (PostToolUse) every tool,
and once when a session ends (SessionEnd).
It sends the event as JSON on stdin and reads the decision from stdout and the
exit code.

Interface: `run(stdin, stdout, stderr, journal, vaults, names) -> exit code`.

Errors produce blocking or masking responses. Runtime enforcement still needs
validation against Claude Code's tool-result schemas and failure behavior.
"""

from __future__ import annotations

import json
from typing import Protocol, TextIO

from privacy_guard.claude_code.deadline import ANSWER_DEADLINE_SECONDS, AnswerGate
from privacy_guard.claude_code.document_scope import is_document_read
from privacy_guard.claude_code.edit_policy import before_edit
from privacy_guard.claude_code.failed_tool import protect_failed_tool
from privacy_guard.claude_code.protection import protect_tool_output
from privacy_guard.claude_code.shell_failures import SHELL_TOOLS, before_shell
from privacy_guard.claude_code.tool_failures import inspection_failed
from privacy_guard.claude_code.write_restoration import process_write_result
from privacy_guard.claude_code.responses import (
    POST_TOOL_USE,
    POST_TOOL_USE_FAILURE,
    PRE_TOOL_USE,
    SESSION_END,
    SESSION_START,
    HookResult,
    allow,
    block,
    deny,
)
from privacy_guard.core.insee_names import local_name_detector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from privacy_guard.diagnostics import record_failure, stage

FAILURE_MESSAGE = "Privacy Guard: internal error, action blocked for safety."
# Instant name detection for everything that is not a document.
QUICK_NAMES = local_name_detector()


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
        names: NameService,
        deadline_seconds: float = ANSWER_DEADLINE_SECONDS) -> int:
    """Handles a full call (read, decide, write)
    and returns the exit code."""

    try:
        with stage('input_read'):
            raw = stdin.read()
    except Exception as error:
        record_failure(journal, None, None, error)
        raw = ''  # Invalid input produces the existing conservative block response.
    gate = AnswerGate(lambda answer: _write(answer, stdout, stderr, journal))
    timer = gate.deadline(deadline_seconds, lambda: _expired(raw, journal))
    try:
        result = _handle_safely(raw, journal, vaults, names)
    finally:
        timer.cancel()
    gate.answer(result)
    return gate.written.exit_code


def _write(result: HookResult, stdout: TextIO, stderr: TextIO, journal: Journal) -> None:
    try:
        with stage('output_write'):
            stdout.write(result.stdout)
            stderr.write(result.stderr)
            # The deadline path ends with os._exit, which does not flush buffers.
            stdout.flush()
            stderr.flush()
    except Exception as error:
        record_failure(journal, None, None, error)
        raise  # A broken output pipe cannot carry a guaranteed replacement.


def _expired(raw: str, journal: Journal) -> HookResult:
    """The fail-closed answer for this event when the deadline comes first."""
    event, payload = PRE_TOOL_USE, None
    try:
        payload = json.loads(raw)
        candidate = payload.get("hook_event_name")
        event = candidate if isinstance(candidate, str) else event
    except Exception:
        pass  # Unreadable input keeps the most cautious assumption.
    tool = payload.get("tool_name") if isinstance(payload, dict) else None
    record_failure(journal, event, tool, at='answer_deadline', category='timeout')
    return fail_closed(event, payload)


def handle(payload: dict,
           journal: Journal,
           vaults: VaultStore,
           names: NameService) -> HookResult:
    """Decides what happens to an event: protect tool results without returning originals in tool inputs,
    warm the name service up when a session starts, forget the session's values when it ends."""
    event = payload["hook_event_name"]
    session_id = payload["session_id"]
    bind_context = getattr(journal, "bind_context", None)
    if callable(bind_context):
        try:
            bind_context(event, session_id)
        except Exception:
            pass  # Optional desktop metadata must not affect enforcement.
    with stage('event_journal'):
        journal.record(event, payload.get("tool_name", "?"))

    if event == SESSION_START:
        # Load the NER model while the user writes the first prompt.
        with stage('service_start'):
            names.ensure_running()
        return allow()
    if event == SESSION_END:
        with stage('session_close'):
            vaults.close_session(session_id)
        return allow()

    if event == PRE_TOOL_USE:
        with stage('tool_policy'):
            if payload.get("tool_name") in SHELL_TOOLS:
                return before_shell(payload)
            return before_edit(payload)

    document = is_document_read(payload)
    with stage('session_open'):
        core = PrivacyCore(vaults.session(session_id), names if document else QUICK_NAMES)
    if event == POST_TOOL_USE_FAILURE:
        return protect_failed_tool(payload, core, journal)
    if event == POST_TOOL_USE:
        report = getattr(journal, "record_protection", None)
        report = report if callable(report) else None
        if payload.get("tool_name") == "Write":
            return process_write_result(payload, core, report=report, failures=journal)
        # Read after detection: the service reports a model that could not load.
        reduced = (lambda: getattr(names, "reduced", None)) if document else None
        return protect_tool_output(payload, core, report, reduced)

    return allow()


def fail_closed(event: str, payload: object = None) -> HookResult:
    """Stop post-tool processing; mask recognized schemas without guessing others."""
    if event in {POST_TOOL_USE, POST_TOOL_USE_FAILURE}:
        return inspection_failed(event, payload)
    return deny(FAILURE_MESSAGE) if event == PRE_TOOL_USE else block(FAILURE_MESSAGE)


def _handle_safely(raw_payload: str,
                   journal: Journal,
                   vaults: VaultStore,
                   names: NameService) -> HookResult:
    # Most cautious assumption until the event has been read.
    event = PRE_TOOL_USE
    payload = None

    try:
        with stage('payload_parse'):
            payload = json.loads(raw_payload)
            if not isinstance(payload, dict):
                raise ValueError("Hook event must be an object")
            candidate = payload.get("hook_event_name", PRE_TOOL_USE)
            if not isinstance(candidate, str):
                raise ValueError("Hook event name must be a string")
            event = candidate
        return handle(payload, journal, vaults, names)

    except Exception as error:
        # Deliberately broad: whatever the error, fail closed.
        tool = payload.get('tool_name') if isinstance(payload, dict) else None
        record_failure(journal, event, tool, error)
        return fail_closed(event, payload)
