# Threat model

Status: design requirements and source-based concerns, not a completed audit. Owner: project maintainer role, to be assigned before public release. Revisit on every supported agent/version, extraction path, restoration policy or cipher change.

## Assets and disclosure paths

Assets: personal values and credentials, session mappings and keys, original local documents, agent settings, model artifacts, service authentication keys, and the accuracy of protection status.

The disclosure boundary is the point where content becomes available to a model or another unapproved recipient. Tool execution can also disclose values through network requests, subprocesses, environment variables and files watched by other software. Vault ciphertext does not protect values after an authorized decryption.

## Adversaries and assumptions

- Accidental agent overreach while performing a legitimate task.
- Prompt injection in a document or tool output, including requests to decode, restore or transmit private values.
- Tools/plugins returning unexpected shapes, binary or encoded content, failure output or misleading metadata.
- A contributor or dependency introducing a privacy regression.
- A process running as the same user can access user-owned configuration and potentially decrypt DPAPI data; this prototype is not an isolation mechanism against it.

Assume a trusted OS, a user deliberately choosing the installed build, and synthetic data during evaluation. Administrator malware, a compromised kernel and secrets typed directly into user prompts are outside the present scope. These exclusions do not excuse leakage on a claimed covered path.

## Required invariants

| ID | Intended invariant | Evidence required |
| --- | --- | --- |
| INV-01 | Required inspection completes before disclosure on each covered path | Instrumented real-agent success/failure/timeout tests |
| INV-02 | Inspection and inference require no external content upload | Offline operation and outbound-request observation |
| INV-03 | Persisted original mappings use a supported OS cipher | Cipher tests plus filesystem/backup review |
| INV-04 | A value has stable tokens only inside its own session | Concurrent, collision and cross-session tests |
| INV-05 | Restoration needs explicit authorized destination and operation | Denied egress, delegated-tool and malicious-command tests |
| INV-06 | Journals contain no inspected values or recoverable mappings | Synthetic value checks including event/tool metadata injection |
| INV-07 | Capability loss changes visible status and policy outcome | Missing model, removed hooks, stopped process and unsupported-output scenarios |
| INV-08 | Installation/removal preserves unrelated user settings | Temporary settings plus interruption/recovery tests |

The word “required” is a policy choice to be recorded. A degraded heuristic mode cannot quietly qualify as model-enabled name coverage.

## Main threats and treatment

| Threat | Current exposure | Required treatment / release evidence |
| --- | --- | --- |
| Hook absent, disabled, killed or timed out | Handler-level exception logic cannot enforce outside its process | Constrained execution or another enforceable gate; test absence and termination |
| Invalid replacement payload | Failure fallback returns a string even for structured output | Schema-valid per-tool fallback; observe the actual model-boundary result |
| Competing transformations | Registration order is not evidence of exclusive control | Conflicting-hook and plugin tests |
| Restored shell argument leaks or executes | Bash can send values to a network or interpret shell metacharacters | Destination-aware restoration; deny unsupported shell restoration; execution constraints |
| Local Write/Edit creates a remote effect | A path may point to synced folders, watched files, startup scripts or configuration | Authorized roots, canonical path checks and user-scoped operation policy |
| Detector false negative | Names can be missed; sensitive context is not always a pattern | Separate detection metrics from enforcement evidence; corpus expansion |
| Unknown representations | Keys, binary values, images, encoding and unsupported schemas can bypass string mapping | Explicit rejection or verified extraction; never infer coverage from recursive mapping |
| Failed tools or injected context | Only selected events are currently registered | Path inventory and real-agent canary tests before covering them |
| Vault misuse | Same-user decryption, short token identifiers, concurrent collision and cleanup races | Access model, concurrency tests, collision policy and retained-session policy |
| Service authentication / denial of service | Shared key file accessible to its owner; peers may stall requests | Permissions, bounded frames, global deadline and malformed-peer tests |
| Journal spoofing | Event and tool name are not sanitized in the journal | Bounded allowlisted metadata; no arbitrary injected lines or paths |
| Dependency/model tampering | Hashes verify expected model bytes but rely on a trusted manifest | Reviewed build provenance, signed release strategy, dependency inventory |
| Settings update interrupted | Direct settings writes and deployment transitions | Atomic recoverable install and rollback evidence |

## Public claim rules

Use “pseudonymizes detected values in the tested tool-result paths.” Do not say “no personal data ever leaves,” “all actions are protected,” “anonymized,” or “tamper-proof” without evidence for those exact statements.

The official [hook reference](https://code.claude.com/docs/en/hooks) documents that command-hook timeouts do not block `PreToolUse`, matching hooks run concurrently, and post-tool processing occurs after effects and may follow telemetry capture. This is why hooks alone are insufficient evidence of mandatory mediation. These are upstream contract observations; reproduction for a supported version remains a release task.

## Security review process

Each privacy-affecting change identifies the touched invariants, adds a synthetic regression, records the supported environment and updates the compatibility matrix. A finding is closed only when its acceptance evidence exists. Internal tests and benchmarks do not close a real-agent delivery finding on their own.

Keep exploit details private once a reporting channel exists; use sanitized issue summaries for planning. See [SECURITY.md](../../SECURITY.md) and [release gates](../releasing.md).
