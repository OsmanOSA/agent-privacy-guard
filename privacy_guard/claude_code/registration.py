"""Registration of the Privacy Guard hook in the Claude Code configuration.

Pure functions over the content of settings.json: no file I/O here, so
everything can be tested without touching the disk.

Our entries are recognised by MARKER in the hook command.
The user's own hooks are never modified.
"""

from __future__ import annotations

import copy

MARKER = ".privacy-guard"
HOOK_EVENTS = ("PreToolUse", "PostToolUse", "SessionStart", "SessionEnd")
# Above the 25 s the hook may wait for the NER model's first load, so a slow
# start fails closed in our code instead of the hook being killed.
HOOK_TIMEOUT_SECONDS = 30


def register(settings: dict, command: str) -> dict:
    """Returns a copy of the settings with our hook first on every event.

    Idempotent: a previous registration is replaced, never duplicated.
    """
    updated = unregister(settings)
    hooks = updated.setdefault("hooks", {})
    for event in HOOK_EVENTS:
        hooks[event] = [_hook_group(command)] + hooks.get(event, [])
    return updated


def unregister(settings: dict) -> dict:
    """Returns a copy of the settings without our hooks."""
    updated = copy.deepcopy(settings)
    hooks = updated.get("hooks", {})
    for event in HOOK_EVENTS:
        remaining = [group for group in hooks.get(event, []) if not _is_ours(group)]
        if remaining:
            hooks[event] = remaining
        else:
            hooks.pop(event, None)
    if not hooks:
        updated.pop("hooks", None)
    return updated


def registered_events(settings: dict) -> dict[str, bool]:
    """Tells, for each event, whether our hook is registered on it."""
    hooks = settings.get("hooks", {})
    return {event: any(_is_ours(group) for group in hooks.get(event, [])) for event in HOOK_EVENTS}


def _hook_group(command: str) -> dict:
    # The "*" matcher applies the hook to every tool (MCP tools included) and,
    # for SessionStart and SessionEnd, to every way a session can start or end.
    return {
        "matcher": "*",
        "hooks": [{"type": "command", "command": command, "timeout": HOOK_TIMEOUT_SECONDS}],
    }


def _is_ours(group: dict) -> bool:
    return any(MARKER in hook.get("command", "") for hook in group.get("hooks", []))
