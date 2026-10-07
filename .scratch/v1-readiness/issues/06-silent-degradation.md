# 06 — Silent degradation without the name model

Status: open
Priority: P0 leak
Blocked by: none

## Evidence

On 2026-10-07 the model could not load (`bad allocation`: 514 MB of commit memory left
on a 16 GB machine, OneDrive holding 7.5 GB). When this happens during a session, the
hook falls back to heuristics and names can pass without the user knowing
(heuristic baseline: 19 of 35 names). Related: SEC-04.

## Acceptance

- Choose the policy explicitly: block document reads while the model is unavailable,
  or allow them with a visible notification. Default for V1: block with a clear message.
- The notification states the cause category (memory, missing files) without content.
- Harness scenario with the model unavailable proves the chosen behaviour.
