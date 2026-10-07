"""Restore a successful local Write on disk and keep its model-facing result protected.

Interface: process_write_result(payload, core, restorer=None) -> HookResult.
Normal tool permissions have already run. No original content or updatedInput is
returned; generic status feedback accompanies the protected tool result.
"""

from __future__ import annotations

import json
from typing import Callable

from privacy_guard.claude_code.protection import protect_tool_output
from privacy_guard.claude_code.notices import RESTORED_NOTICE, RESTORE_FAILED_NOTICE, notify
from privacy_guard.claude_code.responses import POST_TOOL_USE, HookResult
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.exports.written_file import WrittenFileRestorer
from privacy_guard.protection_summary import ProtectionSummary
from privacy_guard.diagnostics import record_failure, stage


def process_write_result(payload: dict, core: PrivacyCore,
                         restorer: WrittenFileRestorer | None = None,
                         report: Callable[[ProtectionSummary], None] | None = None,
                         failures=None) -> HookResult:
    result = protect_tool_output(payload, core, report)
    if payload.get("hook_event_name") != POST_TOOL_USE or payload.get("tool_name") != "Write":
        return result
    writer = restorer if restorer is not None else WrittenFileRestorer()
    try:
        with stage('restoration'):
            changed = writer.restore(payload.get("tool_input"), core.restore)
    except (OSError, ValueError, RuntimeError) as error:
        record_failure(failures, payload.get('hook_event_name'), 'Write', error)
        notice = "Privacy Guard: local restoration failed. Verify the file locally before using it."
        user_notice = RESTORE_FAILED_NOTICE
    else:
        if not changed:
            return result
        notice = "Privacy Guard: personal values restored in the local file. Continue using session tokens."
        user_notice = RESTORED_NOTICE
    response = json.loads(result.stdout) if result.stdout else {"hookSpecificOutput": {"hookEventName": POST_TOOL_USE}}
    response["hookSpecificOutput"]["additionalContext"] = notice
    return notify(HookResult(result.exit_code, stdout=json.dumps(response, ensure_ascii=False), stderr=result.stderr), user_notice)
