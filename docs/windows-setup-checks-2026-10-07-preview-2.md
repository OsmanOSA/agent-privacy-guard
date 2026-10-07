# Windows setup checks — 0.1.0-preview.2 — 2026-10-07

Environment: native Windows 11 Home x64, build 10.0.26200. Builder Python 3.12;
packaged Python 3.14.8. Claude Code 2.1.292 (VS Code extension binary) with the
PowerShell tool enabled, as for claude.ai accounts on Windows. This is a development
machine, not a clean Windows VM.

Built from the working tree of commit `9599d77` plus the setup changes committed with
this receipt: every fix of the V1 readiness items 01 to 06, a lighter runtime and the
installation-directory check.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `PrivacyGuard-0.1.0-preview.2-windows-x64.exe` | 305832808 | `f821df18e92da8e45294df4dc8b044fb4d170e7c4d101d70fe66687757b43cbf` |
| `PrivacyGuard-Test-0.1.0-preview.2-windows-x64.exe` | 305832874 | `754de3857bf3f04be042f9a4017bbd3359b6936b23a7a7e9adce44ea9241d0e4` |

## Payload changes since preview.1

- The runtime no longer ships Python's documentation, C headers, import libraries,
  IDLE or ensurepip: about 435 MB installed instead of 510, 1,076 fewer files.
- The longest payload path is now 126 characters (was 264 with the documentation). The
  build derives the longest valid installation directory, 107 characters, and the
  installer refuses a longer one before copying anything.
- Setup failures show one French sentence. The model probe reports its cause (memory,
  incomplete model, system library) instead of a generic message.

## Checks on the TEST-IDENTITY executable

- `tools/check_windows_setup.py`, profile path with a space and an accented
  character: silent setup, bundled model and INSEE, document and Python hooks,
  restoration and reread, reinstallation preserving the vault, uninstall preserving
  unrelated settings, real profile unchanged.
- A 152-character installation directory: refused with exit code 1, the message
  "Le dossier d'installation est trop long (152 caractères, 107 au maximum)", nothing
  copied.
- `tools/check_model_boundary.py` without `--source`, i.e. the executable itself:

| Scenario | Result |
| --- | --- |
| read-csv, bash-cat, grep-content, parallel-reads, secret-env | tokens only |
| bash-failure-status, -grep, -exit; powershell-failure, -failure-exit | tokens only |
| powershell-get-content, powershell-notes, bash-cp1252 | tokens only |
| write-restore-reread | tokens only; originals restored on disk |
| hook-in-powershell (no Git Bash) | tokens only |
| stalled-name-service | hook answered at its deadline; nothing sent |
| hook-launch-error (runtime missing) | tool refused before it ran |
| model-unavailable | e-mail masked, one free-text name passed, reduced warning recorded (founder's option B) |
| hook-timeout (interpreter stalled before our code) | all canaries: residual, outside the hook |
| control-unprotected-read | all canaries (harness sensitivity) |

No uninstall registry entry remained after the runs. The full source suite passed.

## Not covered yet

A clean Windows account without Python, an interactive VS Code session, an upgrade from
preview.1, Authenticode signing, subagents, MCP results, compaction and resumed sessions
(V1 readiness items 08 and 09). Hook refusals still carry the hook command, with the
Windows user name, into model context (item 11). OCR and binary documents are deferred
to V2.
