# 07 — Rebuild and harden the setup

Status: open
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
