# 06 — Silent degradation without the name model

Status: done
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

## Comments

2026-10-07, founder's decision: option B, continue in reduced mode with a visible
warning (not the blocking default proposed above).

- Before: with an installed model that fails to load, the service raised and the hook
  masked the whole document and stopped the session (the agent was blinded); without
  an installed model, the heuristic ran silently.
- `service/reduced_names.py`: the heuristic answers instead, and every answer carries a
  fixed reason, `model_files` (missing or modified files, reinstall) or
  `model_runtime` (memory, system). Never an exception text.
- The warning goes out even when nothing was found, the case where names pass:
  `ProtectionSummary` carries the reason into the Claude Code message
  ("détection des noms réduite … certains noms peuvent rester visibles"), the
  content-free protection journal and the desktop card ("Protection réduite").
- Boundary scenario `model-unavailable` (model file damaged): the source engine keeps
  the e-mail masked, lets the free-text name through (accepted by option B) and records
  the reduced warning; the preview.1 setup masks everything and stops, with no warning.
- Benchmark in normal mode unchanged (names 97% / 100%, 0 false alarm).
- Follow-ups: a `model_runtime` reduction lasts until the service restarts (idle hour
  or new install); a model that loads but fails on one text still fails closed.
