"""Restore the Excel workbooks a successful shell command names, after it ran.

Agents produce workbooks with scripts (`python -c "...to_excel('clients.xlsx')"`).
Shell commands never receive original values, so the cells hold session tokens.
After the command succeeds, each existing .xlsx/.xlsm workbook named in it gets this
session's values back (exports/written_workbook.py). A workbook a script writes
without naming it in the command comes from a script file, which Write restoration
already gave the real values.

Background commands are skipped: their workbook may still be being written.

Interface: process_shell_result(payload, core, restorer=None, report=None, failures=None, reduced=None)
           -> HookResult; `reduced` as in protection.protect_tool_output.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from privacy_guard.claude_code.protection import protect_tool_output
from privacy_guard.claude_code.responses import POST_TOOL_USE, HookResult
from privacy_guard.claude_code.write_restoration import with_restoration_notice
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.diagnostics import record_failure, stage
from privacy_guard.exports.written_workbook import WorkbookRestorer
from privacy_guard.protection_summary import ProtectionSummary

# A workbook path: double-quoted, single-quoted, or a bare word of the command.
_WORKBOOK = re.compile(r"""(?:"([^"\r\n]+?\.xls[xm])"|'([^'\r\n]+?\.xls[xm])'|([^\s"'<>|;&()=,]+?\.xls[xm]))(?![\w.])""",
                       re.IGNORECASE)
_MAX_WORKBOOKS = 10


def process_shell_result(payload: dict, core: PrivacyCore, restorer: WorkbookRestorer | None = None,
                         report: Callable[[ProtectionSummary], None] | None = None,
                         failures=None, reduced=None) -> HookResult:
    result = protect_tool_output(payload, core, report, reduced)
    arguments = payload.get("tool_input")
    if (payload.get("hook_event_name") != POST_TOOL_USE or not isinstance(arguments, dict)
            or arguments.get("run_in_background")):
        return result
    paths = named_workbooks(arguments.get("command"), payload.get("cwd"))
    if not paths:
        return result
    workbooks = restorer if restorer is not None else WorkbookRestorer()
    restored = False
    try:
        with stage('restoration'):
            for path in paths:
                restored = workbooks.restore(path, core.restore) or restored
    except (OSError, ValueError, RuntimeError) as error:
        record_failure(failures, POST_TOOL_USE, payload.get("tool_name"), error)
        return with_restoration_notice(result, failed=True)
    return with_restoration_notice(result, failed=False) if restored else result


def named_workbooks(command: object, cwd: object) -> list[str]:
    """Absolute paths of the workbooks a command names, relative ones resolved against cwd."""
    if not isinstance(command, str):
        return []
    found = []
    for match in _WORKBOOK.finditer(command):
        path = Path(next(group for group in match.groups() if group))
        if not path.is_absolute():
            if not isinstance(cwd, str) or not cwd:
                continue
            path = Path(cwd) / path
        if str(path) not in found:
            found.append(str(path))
    return found[:_MAX_WORKBOOKS]
