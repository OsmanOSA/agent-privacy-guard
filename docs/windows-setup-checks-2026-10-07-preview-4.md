# Windows setup checks — 0.1.0-preview.4 — 2026-10-07

Environment: native Windows 11 Home x64, build 10.0.26200. Builder Python 3.12;
packaged Python 3.14.8. Claude Code 2.1.292 (VS Code extension binary) with the
PowerShell tool enabled, as for claude.ai accounts on Windows. This is a development
machine, not a clean Windows VM.

Built from a clean worktree of commit `19cf405`: every fix of the V1 readiness items
01 to 08 and 11 to 13. This is the build frozen for the founder's real-use tests.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `PrivacyGuard-0.1.0-preview.4-windows-x64.exe` | 305846489 | `aab2cc984c68704ed94b39ad3feaadf728b0c0dcbdc7e21b052eb578e267996f` |
| `PrivacyGuard-Test-0.1.0-preview.4-windows-x64.exe` | 305846517 | `fd08cb7f51a885edb46d19d8f6d6045e5a34306c9628375354a6d9b9d2dff426` |

Longest valid installation directory: 107 characters.

## Changes since preview.3

- Source code and configuration files (`.py`, `.sql`, `.json`, `.yaml`, `.env*`…) get
  their personal values back after Write, like documents; Edits carrying placeholders
  in them take the Write route (item 13).
- No file tool may write a redacted secret marker: rewriting a `.env` used to replace
  the real secret for good (item 13).

## Checks on the TEST-IDENTITY executable

- `tools/check_windows_setup.py`, profile path with a space and an accented character:
  passed (silent setup, bundled model and INSEE, document and Python hooks, restoration
  and reread, reinstallation preserving the vault, uninstall preserving unrelated
  settings, real profile unchanged).
- `tools/check_model_boundary.py` without `--source`, i.e. the executable itself:
  every scenario of the preview.3 receipt passes again, plus:

| Scenario | Result |
| --- | --- |
| write-python | tokens only in model context; name and e-mail restored on disk |
| write-redacted-secret | Write refused; `.env` keeps its real secret |

Expected leaks, unchanged: mcp-error (documented V1 limit), model-unavailable (one
free-text name, reduced warning recorded, option B), hook-timeout (interpreter stalled
before Privacy Guard's code), control-unprotected-read (harness sensitivity).

## Not covered yet

An interactive VS Code session and a clean Windows account without Python (item 08,
with the founder), an upgrade from an earlier preview, Authenticode signing (item 09).
OCR and binary documents are deferred to V2.
