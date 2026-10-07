# 03 — Explicit exit in a shell command

Status: done
Priority: P0 leak
Blocked by: none

## Evidence

Scenario `bash-failure-exit` (`cat notes.md; exit 3`) still leaks a name and an
e-mail. `exit` (and Bash `set -e`) ends the shell before the trailer of
`shell_failures.py` runs, so the output takes PostToolUseFailure, which Claude Code
sends unchanged. Subshells or traps would contain it but make Claude Code ask for
approval on every command.

## Acceptance

- PreToolUse refuses a shell command containing `exit` or `set -e` / `errexit`
  outside quoted text, with a short instruction so the agent rewrites it
  (e.g. use `|| true` or a condition). Same for PowerShell `exit`.
- No false refusal for the word inside quotes (commit messages, echo).
- `bash-failure-exit` passes; check that the agent retries successfully in the harness.

## Comments

2026-10-07, fixed:

- `claude_code/shell_exits.py` spots constructs that end the shell before the trailer:
  Bash `exit N`, bare `exit`, `set -e` / `errexit`, `exec cmd`; PowerShell `exit N`,
  `throw`, `-ErrorAction Stop`, `$ErrorActionPreference = 'Stop'`. Only where a command
  starts, outside quotes, comments, heredocs and here-strings; `exit 0` is allowed.
- `before_shell` refuses them (PreToolUse exit 2) with an instruction to rewrite.
- Boundary scenarios `bash-failure-exit` and `powershell-failure-exit` (refused
  attempt, then the agent's rewrite) pass on Claude Code 2.1.292; no regression on the
  other shell scenarios.
- Follow-up in item 11: Claude Code prefixes the refusal with the hook command path,
  which carries the Windows user name into model context.
