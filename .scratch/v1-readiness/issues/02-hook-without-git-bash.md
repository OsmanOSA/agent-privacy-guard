# 02 — Hook command without Git Bash

Status: done
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

## Comments

2026-10-07, fixed:

- Probe with a masking hook on Claude Code 2.1.280 and 2.1.292: the string command
  runs in Git Bash but never starts with `"shell": "powershell"`; the exec form
  (`command` = interpreter, `args` = [app]) runs under both.
- `registration.command_handler` registers the exec form. Our entries are recognised
  by the marker in the command or its arguments, so preview.1 string entries are
  replaced on upgrade; the setup uninstaller accepts both forms as its own.
- Boundary scenario `hook-in-powershell` (hooks forced to PowerShell): the preview.1
  setup leaks all 6 canaries; the source engine passes with 6 tokens. The other 16
  scenarios are unchanged.
- Item 05 can now rely on the exec form: a missing interpreter no longer depends on a
  shell's exit code.
