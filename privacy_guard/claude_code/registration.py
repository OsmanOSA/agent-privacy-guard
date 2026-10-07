"""Registration of the Privacy Guard hook in the Claude Code configuration.

Pure functions over the content of settings.json: no file I/O here, so
everything can be tested without touching the disk.

Interface:
    command_handler(executable, app) -> dict      the hook handler to register
    register(settings, handler) / unregister(settings) -> dict
    registered_events(settings) -> {event: bool}
    owned_targets(settings) -> set of (command, args) for every handler of ours

The handler uses Claude Code's exec form (`command` + `args`): the interpreter
starts directly, without a shell. A shell command string only works in Git Bash;
without Git Bash, Claude Code runs hooks in PowerShell, where `"python" "app"` is a
parse error, the hook never starts and every original reaches the model
(observed with Claude Code 2.1.280 and 2.1.292).

Our entries are recognised by MARKER in the command or its arguments, which also
covers string-form entries written by earlier versions. The user's own hooks are
never modified.
"""

from __future__ import annotations

import copy

MARKER = ".privacy-guard"
HOOK_EVENTS = ("PreToolUse", "PostToolUse", "PostToolUseFailure", "SessionStart", "SessionEnd")
# Above the 25 s the hook may wait for the NER model's first load, so a slow
# start can stop in our code before the hook is killed. A platform-level timeout
# still discards our response; registration alone is not mandatory enforcement.
HOOK_TIMEOUT_SECONDS = 30


def command_handler(executable: str, app: str) -> dict:
    """The exec-form handler that runs the deployed app with the given interpreter."""
    return {"type": "command", "command": executable, "args": [app], "timeout": HOOK_TIMEOUT_SECONDS}


def register(settings: dict, handler: dict) -> dict:
    """Returns a copy of the settings with our hook first on every event.

    Idempotent: a previous registration is replaced, never duplicated.
    """
    updated = unregister(settings)
    hooks = updated.setdefault("hooks", {})
    for event in HOOK_EVENTS:
        hooks[event] = [_hook_group(handler)] + hooks.get(event, [])
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


def owned_targets(settings: dict) -> set[tuple[str, tuple]]:
    """What each of our handlers runs, so an uninstaller can check it owns them."""
    hooks = settings.get("hooks", {})
    return {(handler.get("command", ""), tuple(handler.get("args") or ()))
            for event in HOOK_EVENTS for group in hooks.get(event, [])
            for handler in group.get("hooks", []) if _handler_is_ours(handler)}


def _hook_group(handler: dict) -> dict:
    # The "*" matcher applies the hook to every tool (MCP tools included) and,
    # for SessionStart and SessionEnd, to every way a session can start or end.
    return {"matcher": "*", "hooks": [dict(handler)]}


def _is_ours(group: dict) -> bool:
    return any(_handler_is_ours(handler) for handler in group.get("hooks", []))


def _handler_is_ours(handler: dict) -> bool:
    arguments = handler.get("args") or ()
    return MARKER in handler.get("command", "") or any(
        isinstance(argument, str) and MARKER in argument for argument in arguments)
