# 05 — Hook launch failure

Status: done
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

## Comments

2026-10-07, fixed:

- Only PreToolUse exit 2 blocks a tool, and a hook that cannot start gives no exit
  code. PreToolUse now goes through a PowerShell guard (`registration.guard_handler`):
  it runs the app and answers 2 with a fixed message when the interpreter is missing
  or the hook fails. Other events keep the exec form; with no tool allowed to run,
  they have nothing to leak.
- Probes on Claude Code 2.1.292: the guard keeps stdin and UTF-8 output intact both
  ways (accented commands, `⟦…⟧` tokens) and costs about 0.15 s per tool call.
- Boundary scenario `hook-launch-error` (interpreter path made missing): the preview.1
  setup leaks all 6 canaries; the source engine refuses the tool before it runs. The
  full campaign (19 scenarios) passes through the guard.
- Harness lesson: an `args` key, even empty, turns a shell handler into exec form.
- Residuals: a machine where PowerShell is forbidden; a stall before our code runs
  (`hook-timeout`, item 04).
