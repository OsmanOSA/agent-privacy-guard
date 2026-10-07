# 02 — Hook command without Git Bash

Status: open
Priority: P0 leak
Blocked by: none

## Evidence

Claude Code runs command hooks in Git Bash when it is installed, otherwise in
PowerShell (hooks reference, 2026-10-07). The registered command is
`"<python>" "<app>"`, which is bash syntax; in PowerShell a quoted path followed by an
argument is a parse error. On a machine without Git Bash the hook would probably never
start, which releases every original (see item 05). Not tested yet.

Without Git Bash, Claude Code also drops the Bash tool and uses only PowerShell.

## Acceptance

- Reproduce in the harness with a hook shell forced to PowerShell (`"shell": "powershell"`)
  and confirm the outcome.
- Make the registered command independent of the shell, e.g. exec form
  (`command` = interpreter, `args` = [app]), and check stdin, exit codes and latency.
- Boundary campaign passes with Git Bash absent from PATH.
