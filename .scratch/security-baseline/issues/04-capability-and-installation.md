# SEC-04 — Make capability status and installation reproducible

Status: open
Priority: P1
Blocked by: none

## Evidence

Three installer tests fail with exit 127 in the baseline's mixed Bash/native Windows combination. `status` reports registration and model assets. Model loading can degrade to heuristics; the baseline misses 16 of 35 name occurrences in that mode.

## Acceptance

- Declare and test a supported native shell/interpreter pair; diagnose encoding as well as path translation.
- Separate registered, detector-ready, degraded, stopped, blocked and verified states in status/reporting.
- Choose strict versus reduced-detection policy explicitly; preserve the selected state across a session.
- Verify actual detector readiness, not merely presence of model files or completion of loading.
- Review custom install roots, global runtime defaults, settings atomicity and interruption recovery.
- Reproduce tests in temporary directories and report separate heuristic/model-enabled scores.

## Comments

The UX state model in docs is a proposal for this work item, not active runtime functionality.
