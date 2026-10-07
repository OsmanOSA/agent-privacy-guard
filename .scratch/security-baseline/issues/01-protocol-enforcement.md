# SEC-01 — Demonstrate schema-correct failure and mandatory mediation

Status: open
Priority: P0
Blocked by: none

## Evidence

Post-tool exception fallback emits a string, although a built-in tool may require a structured result. Launcher initialization errors only return exit 2. Handler catches cannot control a killed or timed-out process. See the dated security baseline and official hooks reference.

## Acceptance

- Enumerate supported response schemas; implement a valid failure transform for each or deny the path earlier.
- Observe synthetic originals absent at an instrumented real-agent model boundary on success, handler error, launch error, malformed replacement, timeout and conflicting hooks.
- If upstream behavior cannot enforce a path, narrow support or choose an enforcement mechanism with a recorded trade-off.
- Pin agent/platform/shell versions and preserve fixture-only receipts; do not install into a live session as part of the test.

## Review

Requires maintainer and independent security review before closing the release blocker.

## Comments

Initial task is design plus evidence; no fix has been implemented by the groundwork.

2026-10-07: first model-boundary evidence in `docs/security/boundary-checks-2026-10-07.md` (Claude Code 2.1.280, fake Messages API). Success paths for Read, Bash, parallel reads, secrets and Write restoration hold. Three paths release originals: `PostToolUseFailure` despite `continue: false`, hook timeout and hook launch failure. Still open.
