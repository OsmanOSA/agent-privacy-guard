# 05 — Hook launch failure

Status: open
Priority: P0 leak
Blocked by: 02

## Evidence

Scenario `hook-launch-error`: when the hook command cannot start (missing runtime),
Claude Code treats it as a non-blocking error and the tool result reaches the model.
Only PreToolUse exit code 2 blocks a tool.

## Acceptance

- The PreToolUse registration blocks the tool when the runtime cannot start, so the
  tool never runs and nothing is left to leak. Design depends on the command form
  chosen in item 02.
- Keep the guard cheap: it runs before every tool.
- `hook-launch-error` passes (tool blocked, no canary).
