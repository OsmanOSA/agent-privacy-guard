# 04 — Hook timeout

Status: done
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

## Comments

2026-10-07, fixed for stalls inside the hook:

- `claude_code/deadline.py`: a timer writes the fail-closed answer (masked result and
  stop, or a refusal) at 40 s and ends the process; a lock lets only the first of the
  normal and deadline answers through. The expiry is journaled as
  `answer_deadline / timeout`, without content.
- Registered timeout raised from 30 s to 45 s: a cold name service may take 8 s to
  connect plus 25 s to answer (33 s), above the old timeout.
- Boundary scenario `stalled-name-service` (the profile's name service suspended):
  the preview.1 setup leaks a name and an e-mail after Claude Code kills the hook; the
  source engine answers at 40 s and nothing reaches the model (82.6 s session: the
  SessionStart warm-up also waits for its deadline).
- Residual: `hook-timeout` replaces the hook by a sleeping process, i.e. a stall before
  our code runs (interpreter start). It still leaks; no code in the hook can cover it.
- UX note: with a stalled service the session waits 40 s at start and 40 s per read
  before stopping. Safe, but slow; item 06 decides what users see then.
