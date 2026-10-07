"""Fixed failure metadata. Never format exceptions, paths or inspected content."""

import sqlite3
from contextlib import contextmanager

EVENTS = frozenset({'PreToolUse', 'PostToolUse', 'PostToolUseFailure', 'SessionStart', 'SessionEnd'})
TOOLS = frozenset({'Read', 'Write', 'Edit', 'Bash', 'Grep', 'Glob', 'NotebookEdit', 'MCP'})
STAGES = frozenset({
    'payload_parse', 'event_journal', 'session_open', 'session_names', 'session_close',
    'service_start', 'detection', 'vault_write', 'vault_commit', 'restoration',
    'output_mapping', 'output_response', 'protection_journal', 'tool_policy',
    'model_loading', 'model_inference', 'failed_tool', 'launcher_init', 'input_read', 'output_write',
})
CATEGORIES = frozenset({
    'timeout', 'permission', 'missing_file', 'sqlite_locked', 'sqlite_corrupt',
    'sqlite_error', 'invalid_data', 'os_error', 'runtime_error', 'unexpected',
    'sensitive_result', 'unsupported_schema', 'installation_unavailable',
})


def fixed(value, allowed, fallback):
    return value if isinstance(value, str) and value in allowed else fallback


@contextmanager
def stage(name):
    """Preserve exception types; the innermost failed stage accompanies them."""
    try:
        yield
    except Exception as error:
        try:
            if getattr(error, '_privacy_guard_stage', None) not in STAGES:
                error._privacy_guard_stage = fixed(name, STAGES, 'unknown')
        except Exception:
            pass
        raise


def failure_details(error, fallback='unknown'):
    name = fixed(getattr(error, '_privacy_guard_stage', fallback), STAGES, 'unknown')
    category = fixed(getattr(error, '_privacy_guard_category', None), CATEGORIES, None)
    if category:
        return name, category
    cause = error
    for _ in range(4):
        if isinstance(cause, sqlite3.Error):
            code = getattr(cause, 'sqlite_errorcode', 0) & 255
            category = ('sqlite_locked' if code in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}
                        else 'sqlite_corrupt' if code in {sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB}
                        else 'sqlite_error')
            return name, category
        cause = cause.__cause__
        if cause is None:
            break
    for types, category in [(TimeoutError, 'timeout'), (PermissionError, 'permission'),
                            (FileNotFoundError, 'missing_file'), ((ValueError, TypeError), 'invalid_data'),
                            (OSError, 'os_error'), (RuntimeError, 'runtime_error')]:
        if isinstance(error, types):
            return name, category
    return name, 'unexpected'


def record_failure(journal, event, tool, error=None, *, at='unknown', category='unexpected'):
    """Optional best-effort journal: logging failure never breaks enforcement."""
    try:
        recorder = getattr(journal, 'record_failure', None)
        if callable(recorder):
            if error is not None:
                at, category = failure_details(error, at)
            recorder(event, tool, at, category)
    except Exception:
        pass
