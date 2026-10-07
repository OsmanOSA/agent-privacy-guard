# 10 — End-of-work summary notification

Status: blocked
Priority: later
Blocked by: 01–08, and detection quality high enough (founder's example: 95%)

## Outcome

When an agent finishes its work, one notification summarizes what was masked and in
which documents (categories, counts, file names; never values). This is the product's
presence, like an agent's end-of-task notification. No interface beyond notifications.

## Notes

- Listen to the `Stop` event; protection records need the session id so several
  terminals and agents stay separate.
- Decide whether per-file notifications remain or only the summary.
