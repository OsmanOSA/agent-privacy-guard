# SEC-05 — Review local persistence, concurrency and metadata

Status: open
Priority: P1
Blocked by: none

## Evidence

Token IDs contain eight hexadecimal characters. Collision checks and atomic individual writes exist, but concurrent collision behavior needs review. The local inference channel uses a shared key stored in user files; journal event/tool metadata is appended as text.

## Acceptance

- Demonstrate same-session consistency and cross-session isolation under parallel hook processes and forced collisions; choose an ID-length/collision policy.
- Document same-user access limits of DPAPI and the channel key; review permissions and backup exposure.
- Bound service frame size, authentication/request lifetime and total hook deadline, including stalled peers and startup waits.
- Allowlist and bound journal metadata; test newlines, injected values, file paths and malicious tool names without raw data output.
- Review abandoned-session cleanup, resume behavior and token retention before vault deletion.
- Record scope of deletion versus secure erasure; avoid promising the latter.

## Comments

Do not introduce custom cryptography as a shortcut.
