# Windows setup checks — 0.1.0-preview.3 — 2026-10-07

Environment: native Windows 11 Home x64, build 10.0.26200. Builder Python 3.12;
packaged Python 3.14.8. Claude Code 2.1.292 (VS Code extension binary) with the
PowerShell tool enabled, as for claude.ai accounts on Windows. This is a development
machine, not a clean Windows VM.

Built from commit `1421e30`: every fix of the V1 readiness items 01 to 08, 11 and 12.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `PrivacyGuard-0.1.0-preview.3-windows-x64.exe` | 305844418 | `90b37330bae0852623bd670ad2a486bc485f8eed3fd4a1f9756ee75d216923c3` |
| `PrivacyGuard-Test-0.1.0-preview.3-windows-x64.exe` | 305844516 | `119dd3c93d7b6fc18edee77024bc2fc5563f0d743de36b999f9c4c85bb419301` |

Longest valid installation directory: 107 characters, as in preview.2.

## Changes since preview.2

- Hook refusals are a JSON `permissionDecision: "deny"`: they no longer carry the hook
  command, with the Windows user name, into model context (item 11).
- Subagents, MCP results, Edit, Glob, resumed and compacted sessions, background
  commands and parallel sessions are covered (item 08). Person names inside file names
  are masked in listings; file tools get the real path locally.
- Technical file names (`per_channel.py`, `01-tool-name-false-positives.md`) are no longer
  taken for person names: 0.22% of 30,000 real file names match instead of 2.2% (item 12).

## Checks on the TEST-IDENTITY executable

- `tools/check_windows_setup.py`, profile path with a space and an accented character:
  silent setup, bundled model and INSEE, document and Python hooks, restoration and
  reread, reinstallation preserving the vault, uninstall preserving unrelated settings,
  real profile unchanged.
- `tools/check_model_boundary.py` without `--source`, i.e. the executable itself:

| Scenario | Result |
| --- | --- |
| read-csv, bash-cat, grep-content, parallel-reads, secret-env | tokens only |
| bash-failure-status, -grep; powershell-failure | tokens only |
| bash-failure-exit, powershell-failure-exit | refused, tokens only, no local path |
| powershell-get-content, powershell-notes, bash-cp1252 | tokens only |
| write-restore-reread | tokens only; originals restored on disk |
| subagent-read, mcp-result, edit-document | tokens only |
| glob-filenames, glob-then-read | masked file name; the real file opened locally |
| resume-history, compaction, background-command, parallel-sessions (3) | tokens only |
| hook-in-powershell (no Git Bash) | tokens only |
| stalled-name-service | session stopped before the result was sent |
| hook-launch-error (runtime missing) | tool refused before it ran |
| model-unavailable | e-mail masked, one free-text name passed, reduced warning recorded (option B) |
| mcp-error | name and e-mail of the error message: documented V1 limit, MCP relay in V2 |
| hook-timeout (interpreter stalled before our code) | all canaries: residual, outside the hook |
| control-unprotected-read | all canaries (harness sensitivity) |

The full source suite passed (485 tests) and the benchmark scores 100% recall and
precision on every category.

## Not covered yet

A clean Windows account without Python, an interactive VS Code session, an upgrade from
preview.1 or preview.2 (item 08, to run with the founder) and Authenticode signing
(item 09). OCR and binary documents are deferred to V2.
