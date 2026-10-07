"""Give file tools the real path behind a pseudonymized file name.

File names that contain a person's name reach the model as tokens
(cv_⟦PERSON_NAME:…⟧.md, core/file_names.py), so the path the agent asks for does not
exist. Founder's choice (2026-10-07, V1 readiness item 08): restore this session's
tokens in the path arguments of local file tools before they run. The value only
reaches the file system; the tool's result is protected again afterwards, with the
same tokens.

Shell commands are excluded: a command can send what it reads elsewhere, so tokens
are never restored there and such a command fails on the unknown path.

Interface: restore_file_paths(payload, open_core) -> HookResult
`open_core()` opens this session's PrivacyCore; it is called only when a path holds a token.
"""

from __future__ import annotations

from typing import Callable

from privacy_guard.claude_code.responses import HookResult, allow, replace_tool_input
from privacy_guard.core.privacy_core import TOKEN_OPENING, PrivacyCore

_PATH_ARGUMENTS = {
    "Read": ("file_path",), "Edit": ("file_path",), "MultiEdit": ("file_path",),
    "Write": ("file_path",), "NotebookEdit": ("notebook_path",), "Glob": ("path",), "Grep": ("path",),
}


def restore_file_paths(payload: dict, open_core: Callable[[], PrivacyCore]) -> HookResult:
    arguments = payload.get("tool_input")
    keys = _PATH_ARGUMENTS.get(payload.get("tool_name"), ())
    if not isinstance(arguments, dict):
        return allow()
    tokenized = [key for key in keys if isinstance(arguments.get(key), str) and TOKEN_OPENING in arguments[key]]
    if not tokenized:
        return allow()
    core = open_core()
    restored = {**arguments, **{key: core.restore(arguments[key]) for key in tokenized}}
    return allow() if restored == arguments else replace_tool_input(restored)
