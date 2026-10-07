"""Spot shell constructs that end a command before its failure can be masked.

`shell_failures` appends a trailer so a failing command still ends with status 0.
An explicit exit ends the shell before that trailer runs: Bash `exit N`, `set -e`,
`exec cmd`; PowerShell `exit N`, `throw`, `-ErrorAction Stop`. The output then takes
PostToolUseFailure, which Claude Code sends to the model unchanged (2.1.292).
Such commands are refused before they run, with an instruction to rewrite them.

Only real commands count: words inside quotes, comments and heredocs or here-strings
are ignored, and an exit must stand where a command starts (`grep exit app.sh` is
fine). `exit 0` is harmless: it ends with success, which the hook can mask.

Interface: ends_shell_early(command, shell) -> bool
"""

from __future__ import annotations

import re

# Where a command can start: beginning, after a separator or a control keyword.
_BASH_START = r"(?:^|[;&|(){}\n]|\b(?:then|do|else|elif)\b)[ \t]*"
_POWERSHELL_START = r"(?:^|[;{}()|\n])[ \t]*"
_NON_ZERO_EXIT = r"exit(?![\w-])(?![ \t]+0\b)"

_BASH_EARLY_END = re.compile(
    _BASH_START + rf"(?:{_NON_ZERO_EXIT}"
    r"|set[ \t]+(?:-[A-Za-z]*e[A-Za-z]*\b|-o[ \t]+errexit\b)"
    r"|exec[ \t]+(?![\d<>&]))", re.MULTILINE)
_POWERSHELL_EARLY_END = re.compile(_POWERSHELL_START + rf"(?:{_NON_ZERO_EXIT}|throw\b)",
                                   re.MULTILINE | re.IGNORECASE)
_POWERSHELL_STOP = re.compile(r"-(?:ErrorAction|ea)[ \t]*:?[ \t]*['\"]?Stop\b"
                              r"|\$ErrorActionPreference[ \t]*=[ \t]*['\"]?Stop\b", re.IGNORECASE)

_BASH_QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")
_POWERSHELL_QUOTED = re.compile(r"'(?:''|[^'])*'|\"(?:`.|[^\"`])*\"")
_COMMENT = re.compile(r"(?:(?<=\s)|^)#[^\n]*", re.MULTILINE)
_BLOCK_COMMENT = re.compile(r"<#.*?#>", re.DOTALL)
_HERE_STRING = re.compile(r"@(['\"])\r?\n.*?\r?\n\1@", re.DOTALL)
_HEREDOC_START = re.compile(r"(?<!<)<<-?(?!<)[ \t]*(['\"]?)([A-Za-z_]\w*)\1")


def ends_shell_early(command: str, shell: str) -> bool:
    """True when the command can end the shell with a failure before the trailer."""
    if shell == "PowerShell":
        code = _COMMENT.sub("", _BLOCK_COMMENT.sub("", _HERE_STRING.sub("", command)))
        return bool(_POWERSHELL_STOP.search(code)
                    or _POWERSHELL_EARLY_END.search(_POWERSHELL_QUOTED.sub("''", code)))
    code = _BASH_QUOTED.sub("''", _without_heredocs(command))
    return bool(_BASH_EARLY_END.search(_COMMENT.sub("", code)))


def _without_heredocs(command: str) -> str:
    kept, delimiter = [], None
    for line in command.split("\n"):
        if delimiter is not None:
            if line.strip() == delimiter:
                delimiter = None
            continue
        kept.append(line)
        match = _HEREDOC_START.search(line)
        if match:
            delimiter = match.group(2)
    return "\n".join(kept)
