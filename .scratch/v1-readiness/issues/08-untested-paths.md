# 08 — Untested paths

Status: open
Priority: P1
Blocked by: none

## Evidence

The boundary campaign does not yet cover these ways content reaches the model.

## Acceptance

Add one harness scenario per path; each gets pass, a fix item, or a documented exclusion:

- Subagent (Agent tool) reading a document.
- MCP tool result and MCP error (errors take PostToolUseFailure).
- Edit, Glob filenames containing names (e.g. `cv_jean_dupont.md`), WebFetch.
- Background shell commands and their later output.
- Context compaction and `--resume` of a session that read documents.
- Two concurrent sessions.
- An interactive VS Code session (not only `claude -p`).
- A clean Windows account without Python.
