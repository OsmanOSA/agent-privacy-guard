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

## Comments

2026-10-07, first batch measured on Claude Code 2.1.292 (harness: subagent scripts,
fixture MCP server `tools/boundary_harness/mcp_fixture.py`, `--resume`):

| Scenario | Outcome |
| --- | --- |
| subagent-read (Agent tool reads a document) | pass: tokens only, in the subagent's and the main conversation |
| edit-document (Edit snippet of a document) | pass |
| resume-history (`--resume` resends earlier results) | pass: the stored history holds tokens |
| mcp-result | was: a name passed (MCP output used quick detection only); fixed: MCP results now use the name model (`document_scope`) |
| mcp-error | leaks: an MCP error takes PostToolUseFailure; the hook detects it, but Claude Code ignores the stop and an MCP call cannot be rewritten to succeed |
| glob-filenames | leaks: `cv_camille_lefebvre.md`; detecting it would make the path unusable unless file tools restore tokens in their path arguments |

Still to measure: background commands, compaction, concurrent sessions, interactive
VS Code, clean machine, WebFetch.

2026-10-07, founder's decisions and fixes:

- mcp-error: documented V1 limit (README "Known limits"); a local MCP relay that also
  masks errors is planned for V2.
- File names: masked and restored locally. `core/file_names.py` finds a given and a
  family name from the INSEE index adjacent in a file name, never developer words
  (`test_data.py`, `read_report.py`). `claude_code/path_restoration.py` restores this
  session's tokens in the path arguments of Read, Edit, Write, NotebookEdit, Glob and
  Grep before they run; shell commands never get originals.
- The benchmark now builds its detectors like the hook and the service (with the INSEE
  index when installed). Trap `benchmark/corpus/file_listing.out` first: names 90% ->
  98% recall, precision 100%, 0 false alarm; heuristic-only 55% / 100%.
- Boundary: glob-filenames and glob-then-read (the agent opens the masked path and
  reads the file) pass; mcp-result passes.
