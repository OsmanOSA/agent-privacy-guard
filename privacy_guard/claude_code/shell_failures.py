"""Keep failed shell commands on the hook path that can mask their output.

Claude Code sends a failed tool's error text to the model as is: PostToolUseFailure
can neither replace it nor stop the request (observed with 2.1.280 and 2.1.292). A
shell command whose final status is non-zero therefore gets a trailer that ends with
status 0, so its output goes through PostToolUse, where the hook replaces it.

The trailer must stay invisible to Claude Code's permission analysis, which checks
the rewritten command. Observed with 2.1.292:
- Bash: `$?`, subshells and traps prompt for approval; `|| echo "literal"` and a bare
  `true` do not. The literal keeps the failure visible to the model; `true` on its
  own line is the fallback when the last line could swallow the trailer.
- PowerShell (the primary shell for claude.ai accounts on Windows): `$?` inside
  `if` prompts; a final `Write-Output ''` line does not. PowerShell prints its own
  error records, so the failure stays visible without the exit status.

`exit`, `set -e` and similar end the shell before the trailer runs: `shell_exits`
spots them and such commands are refused with an instruction to rewrite them.

Interface:
    SHELL_TOOLS                                   tool names handled here
    route_shell_failures(tool_input, shell) -> dict | None   None leaves the call as is
    before_shell(payload) -> HookResult           the PreToolUse answer for a shell call
"""

from __future__ import annotations

from privacy_guard.claude_code.responses import HookResult, allow, deny, replace_tool_input
from privacy_guard.claude_code.shell_exits import ends_shell_early

BASH, POWERSHELL = "Bash", "PowerShell"
SHELL_TOOLS = frozenset({BASH, POWERSHELL})
FAILED_MARKER = "[command failed]"
_BASH_TRAILER = f' || echo "{FAILED_MARKER}"'
_BASH_FALLBACK = "\ntrue"
_POWERSHELL_TRAILER = "\nWrite-Output ''"
# Endings that leave a command incomplete: anything appended would complete it with
# a different meaning (npm test | true), so such a command is left to fail as it is.
_INCOMPLETE_ENDINGS = {BASH: ("\\", "|", "&&"), POWERSHELL: ("`", "|", "&&")}
EARLY_EXIT_GUIDANCE = (
    "Privacy Guard: this command can end the shell before a failure is masked "
    "(exit, set -e, exec, throw or -ErrorAction Stop), so its error text would reach "
    "the model unprotected. Run it again without them, for example with `|| true` "
    "or an `if` test."
)


def before_shell(payload: dict) -> HookResult:
    """Refuse commands that would escape the trailer; rewrite the others."""
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if isinstance(command, str) and ends_shell_early(command, payload.get("tool_name")):
        return deny(EARLY_EXIT_GUIDANCE)
    updated = route_shell_failures(tool_input, payload.get("tool_name"))
    return allow() if updated is None else replace_tool_input(updated)


def route_shell_failures(tool_input: object, shell: object = BASH) -> dict | None:
    """Arguments whose command always ends with status 0, or None if unsafe to change."""
    if shell not in SHELL_TOOLS or not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return None
    stripped = command.rstrip()
    if stripped.endswith(_INCOMPLETE_ENDINGS[shell]):
        return None
    trailer = _bash_trailer(stripped) if shell == BASH else _POWERSHELL_TRAILER
    return {**tool_input, "command": stripped + trailer}


def _bash_trailer(command: str) -> str:
    last_line = command.splitlines()[-1]
    if "<<" in command or "#" in last_line or command.endswith(("&", ";")):
        return _BASH_FALLBACK
    return _BASH_TRAILER
