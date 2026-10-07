# 03 — Explicit exit in a shell command

Status: open
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
