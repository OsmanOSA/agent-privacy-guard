# 11 — Hook refusals disclose the local user path

Status: open
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
