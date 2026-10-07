# 04 — Hook timeout

Status: open
Priority: P0 leak
Blocked by: none

## Evidence

Scenario `hook-timeout`: when the hook exceeds its timeout, Claude Code kills it,
ignores its answer and sends the original result (all canaries observed). The hook
waits up to 25 s for the name model; the registered timeout is 30 s.

## Acceptance

- An internal deadline in the hook process, well under the registered timeout,
  answers with the masked result and a stop before Claude Code kills it.
- The deadline covers every stage (service start, inference, vault), not only the
  name model.
- A harness scenario with a slow name service proves the masked answer arrives.
