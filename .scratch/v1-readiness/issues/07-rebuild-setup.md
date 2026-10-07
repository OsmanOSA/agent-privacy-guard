# 07 — Rebuild and harden the setup

Status: done
Priority: P1
Blocked by: 01, 02, 03, 04, 05, 06

## Evidence

- `dist/` executables predate the fixes of commit 8018c89.
- Installing under a long directory failed: `runtime/Doc/html/_downloads/...` reached
  264 characters with `LongPathsEnabled=0`. The documentation weighs 65 MB and is not
  needed at runtime (install total ≈ 490 MB, name service ≈ 300 MB RAM).
- The setup's detector probe discards stderr, so "could not run on this computer"
  hides the cause (it was a memory allocation failure).
- The failure message mixes French and English.

## Acceptance

- Payload excludes `runtime/Doc` (and other unused parts); setup preflight checks
  path length.
- Probe failure records a content-free cause category (memory, missing file, other).
- One language per message.
- Rebuilt TEST-IDENTITY setup passes the full boundary campaign without `--source`;
  record hashes in a new setup receipt.

## Comments

2026-10-07, done with `0.1.0-preview.2` (receipt:
`docs/windows-setup-checks-2026-10-07-preview-2.md`):

- Payload without Python's documentation, headers, import libraries, IDLE and ensurepip:
  306 MB setup, about 435 MB installed; longest path 126 characters.
- The build derives the longest valid installation directory (107 characters) and the
  installer refuses a longer one before copying (checked with 152 characters).
- `SetupError` carries one French sentence; unexpected errors show a category only. The
  model probe reports memory, incomplete model or system library.
- On the executable itself: the setup check passes and the boundary campaign passes
  every covered scenario; residual `hook-timeout`, accepted `model-unavailable` name.
- Still open elsewhere: clean machine, interactive VS Code, upgrade from preview.1,
  signing (items 08, 09).
