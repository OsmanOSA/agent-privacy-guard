# SEC-02 — Authorize restoration by destination and operation

Status: open
Priority: P0
Blocked by: none

## Evidence

Local tool names currently authorize restoration, including Bash. Core restoration is a direct session lookup without an operation/destination policy. A command can interpret shell metacharacters in a restored value or transmit it externally.

## Acceptance

- Record the personal-data and secret restoration policy separately.
- Authorize exact local output roots/operations; account for canonical paths, links, synced destinations and configuration/script writes.
- Reject remote and delegated destinations; unknown commands do not inherit a local-only designation.
- Use safe structured argument handling rather than string interpolation where supported. A shell blacklist alone is not egress enforcement.
- Test legitimate local file output, malicious token reuse, shell syntax, network effects, unknown/cross-session tokens and prompt injection using synthetic values.
- Decide how the user requests a restored artifact and what happens to tokens in a chat answer.

## Comments

Policy is proposed, not implemented. Closing this task requires observable destination behavior.
