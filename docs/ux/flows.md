# UX flows and state model

Status: proposal, not implemented runtime behavior. The [interactive mockup](privacy-guard.prototype.html) runs locally with synthetic values and no agent connection. Its controls simulate a future capability contract.

## Principles

Make scope understandable before setup. Distinguish installed hooks, working detection and verified paths. Explain a failure with a safe next action. Keep private values and mappings out of diagnostics. A restored local artifact and a model's chat answer are different outputs.

## Setup journey

1. Choose the supported Claude Code/platform/shell combination; other agents appear as future work.
2. Show detection modes and the current limitations before applying changes.
3. Explain where the engine/vault live, which agent settings change, that installation may download a model, and that session mappings can be purged.
4. Register hooks and run synthetic capability checks.
5. Present either verified covered paths (only when real evidence supports the build), reduced detection, an unsupported environment or a failed setup. A green installed indicator alone is insufficient.

Today's CLI performs some of these operations but does not implement this capability-check journey. The installation baseline currently fails in the tested mixed-shell environment.

## Proposed session states

| State | Meaning | Message | Next action |
| --- | --- | --- | --- |
| Not installed | No integration configured | “Claude Code integration is not installed.” | Review setup |
| Registered, unverified | Hooks configured; enforcement evidence incomplete | “Hooks registered. Coverage has not been verified.” | Run synthetic checks |
| Checking | Required local checks are running | “Checking the declared environment and supported paths.” | Wait or stop |
| Verified covered paths | Exact build/environment meets the documented contract | “The listed paths passed compatibility checks. Detection may still miss values.” | Work within scope |
| Degraded detection | A required/optional detector is unavailable | “Name model unavailable. Detection is reduced.” | Stop, repair, or explicitly select a reduced policy if permitted |
| Blocked | Required inspection cannot complete | “This covered action cannot proceed safely.” | Retry after repair or stop |
| Unsupported path | Content/operation lacks validated handling | “This path is not covered by this build.” | Stop or use a supported synthetic workflow |

The “verified” state is a future claim requiring evidence, not a capability of today's status command. Whether reduced mode is allowed on real data is an open policy decision. The mockup permits only an explicitly selected **synthetic** demonstration.

## Working with a document

Use a fictional text fixture. Show what the model would receive as tokens, without showing originals in diagnostics. The final local file may restore authorized personal values through an approved operation. Do not label a model response as automatically restored: today's code restores selected tool arguments only.

If a value is unknown, cross-session or damaged, leave it unresolved and report the problem rather than substituting an invented identity. Exact runtime behavior for incomplete final artifacts must be decided before release.

## Secret and restoration journey

Secrets should have a stricter policy than personal values. The mockup demonstrates a destination decision: approved local artifact versus denied remote/delegated request. This policy is proposed; the current tool-name allowlist is insufficient proof.

The user sees the operation and destination class before restoration, never a private value in the audit trail. Shell/network effects require enforcement beyond a label saying “local.”

## Failure and recovery

- Invalid output: stop the covered workflow, show a neutral reason and point to a synthetic reproducer. Do not offer a default “continue unprotected” button.
- Model unavailable: show reduced detection and known coverage limits; present repair/stop before a reduced-policy choice.
- Unsupported binary/image: say extraction/coverage is unverified; a text-only transformation does not cover the bytes.
- Integration changed: re-check capabilities; status must not remain verified by inertia.
- Removal: explain that integration and mappings are removed while logs/backups may remain; show recovery instructions separately.

## Journal and accessibility

Proposed journal fields: bounded event type, tool class, outcome and detector mode. Today's journal records only event/tool/timestamp, and its metadata validation requires review. Counters in the mockup are synthetic; do not invent prevented-leak totals in production.

Use readable status text as well as color, keyboard-operable controls, visible focus, live announcements for changes and a narrow-screen layout. No telemetry or persistent state is needed for the prototype.

## Scenario review

Ask a participant to configure the simulation, explain the covered paths, notice reduced detection, inspect a fictional document and explain why remote restoration is refused. Record confusion and time to understand, not private transcripts. Use [the UX scenario template](../templates/ux-scenario.md).

## Architecture visual

Open the [Archify target diagram](privacy-target.html). It focuses on incoming tool-result disclosure; restoration is a separate contract. It is a proposed module/control design, not pinned repository evidence; the workspace has no Git identity. Current source behavior is described in [architecture](../architecture.md). Validation and third-party attribution are in [artifact notes](README.md).
