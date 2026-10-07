# 11 — Hook refusals disclose the local user path

Status: done
Priority: P1
Blocked by: none

## Evidence

A PreToolUse refusal through exit code 2 reaches the model as
`PreToolUse:Bash hook error: [<python path> <app path>]: <message>` (Claude Code
2.1.292, boundary scenario `bash-failure-exit`). Both paths contain the Windows user
name (`C:/Users/<name>/...`), so every refusal puts it in model context.

## Acceptance

- Probe whether a JSON `permissionDecision: "deny"` with `permissionDecisionReason`
  reaches the model without the command prefix, and whether it still blocks when the
  user's permission mode would allow the tool.
- If it does, route every refusal (`responses.block`) through it; otherwise record the
  limit and consider an install path without the user name.
- Boundary check: no user-name canary in any request after a refusal.

## Comments

2026-10-07: with the PreToolUse guard (item 05), the prefix now carries the guard's
PowerShell script, which contains both paths. Same fix applies.

2026-10-07, fixed:

- Probe on Claude Code 2.1.292: a JSON `permissionDecision: "deny"` refuses the tool in
  default and bypass permission modes, and the model receives the reason without the
  hook command; exit code 2 also refuses but carries both paths.
- `responses.deny` now answers every tool refusal (edit policy, early shell exits,
  internal PreToolUse failures, the launcher's broken-installation answer and the
  PowerShell guard's missing interpreter). Exit code 2 remains for events without a
  tool decision, and for the guard when the hook fails after writing part of its
  answer (appended JSON would be unreadable, hence non-blocking).
- Boundary: `bash-failure-exit`, `powershell-failure-exit` and `hook-launch-error` are
  refused with no user name in the refusal.
- Limit outside our reach: Claude Code puts the working directory, with the Windows
  user name, in its own system prompt; paths in tool results are not pseudonymized.
