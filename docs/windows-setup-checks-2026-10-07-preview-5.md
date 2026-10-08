# Windows setup checks — 0.1.0-preview.5 — 2026-10-07

Environment: native Windows 11 Home x64, build 10.0.26200. Builder Python 3.12;
packaged Python 3.14.8. Claude Code 2.1.292 (VS Code extension binary) with the
PowerShell tool enabled, as for claude.ai accounts on Windows. This is a development
machine, not a clean Windows VM.

Built from a clean worktree of commit `263cd41`: every fix of the V1 readiness items
01 to 08 and 11 to 15. This build replaces preview.4 for the founder's real-use tests.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `PrivacyGuard-0.1.0-preview.5-windows-x64.exe` | 305852215 | `0a9366ac70023968f700a2ee42377f9dd7831cc0e9cc0483d863bfb541e27ed3` |
| `PrivacyGuard-Test-0.1.0-preview.5-windows-x64.exe` | 305852309 | `1fec0303e50eaa9fe174272a976ef33e7d4f5e0d8d53fca89f04700ece083073` |

Longest valid installation directory: 107 characters.

## Changes since preview.4

- SQL files: reads go through the name model; restoration only inside string literals
  (quotes doubled) and comments; the export command accepts `.sql` (item 14).
- Excel workbooks: commands naming a workbook go through the name model; after a
  successful shell command, the `.xlsx`/`.xlsm` workbooks it names get their values back
  in text cells only, never in formulas (item 15).

## Checks on the TEST-IDENTITY executable

- `tools/check_model_boundary.py` without `--source`, full campaign: every scenario of
  the preview.4 receipt passes again, plus write-sql, shell-xlsx and write-xlsx.
  `read-xlsx` is inconclusive by design: Claude Code refuses binary files, so nothing
  reaches the model. Expected leaks, unchanged: mcp-error, model-unavailable (option B),
  hook-timeout, control-unprotected-read.
- First run under memory pressure (OneDrive held 9.8 GB, 1.7 GB of commit memory free):
  the name model could not load (`MemoryError`), the service reported reduced
  detection as designed, `tools/check_windows_setup.py` failed on its model assertion
  and one of the three parallel sessions was stopped by the hook (fail closed, no leak).
- After OneDrive was restarted (13.7 GB free): `tools/check_windows_setup.py`, profile
  path with a space and an accented character, passed; parallel-sessions (21 tokens),
  bash-cat, powershell-notes, write-sql, shell-xlsx, write-xlsx, subagent-read and
  background-command passed again on the executable.

The full source suite passed (512 tests) and the benchmark scores 100% recall and
precision on every category.

## Not covered yet

An interactive VS Code session and a clean Windows account without Python (item 08,
with the founder), an upgrade from an earlier preview, Authenticode signing (item 09).
OCR is deferred to V2.
