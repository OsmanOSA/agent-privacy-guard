# SEC-03 — Inventory every supported disclosure path

Status: open
Priority: P0
Blocked by: none

## Evidence

Four event types are registered. Transformation covers nested string values, but not dictionary keys, binary content, prior context or all failure events. Hook registration is not an inventory of everything entering model context.

## Acceptance

- Classify successful/failed tool results, file and shell tools, MCP, subagents, metadata, instructions, images/binary data, resumed history and compaction.
- For each path: supported transform, explicit denial or explicit exclusion. Document when the original is already logged or transmitted outside the model path.
- Test hook removal/settings modification/unknown tools and publish the status consequence.
- Observe synthetic canaries through a real-agent harness, including parallel calls and other installed transformations.
- Update the compatibility matrix and user-facing scope for the demonstrated subset only.

## Comments

No universal support claim is implied by this task.

2026-10-07: `Grep` content output reaches the model without name detection (document scope covers Read and shell reads of document files only). Evidence and the list of paths not yet observed: `docs/security/boundary-checks-2026-10-07.md`.
