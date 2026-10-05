# Architecture and adapter contract

Status: source inspection plus proposed contracts, 2026-10-05. A successful unit test of a hook response is not evidence that an agent accepted that response.

## Current flow

1. The installer copies Python source to the user's guard directory and registers command hooks in Claude Code settings.
2. A hook invocation receives a JSON event. The handler records an event and opens a session vault.
3. For a successful tool result, nested **string values** pass through `PrivacyCore.protect`. Non-string values and dictionary keys are left unchanged.
4. The detector combines secret rules, formatted/tabular personal-data rules and a name detector. Document-like reads use the local name process; other outputs use heuristics.
5. Detected spans become tokens. Session mappings are stored through the OS cipher. The adapter emits a replacement tool result.
6. Before tools listed as local run, token-bearing string arguments pass through `PrivacyCore.restore`. The current list includes Bash, Write, Edit, MultiEdit and NotebookEdit.
7. Session end deletes that session's vault and triggers stale-vault cleanup. This is deletion, not guaranteed secure erasure of backups or storage media.

The current hook does not first scan every file for personal data before allowing access. It normally acts on the content returned by a tool. It also does not rewrite the final chat response. Restoration happens in selected tool arguments.

## Existing modules and interfaces

| Module | Interface / seam | Responsibility and current limitation |
| --- | --- | --- |
| `privacy_guard/core/privacy_core.py` | `PrivacyCore(vault, names).protect(text) / restore(text)` | Span replacement and lookup; no destination policy |
| `privacy_guard/core/detector.py` | `SensitiveDataDetector(names).find(text)` | Ordered findings and overlap priorities; unknown data can be missed |
| `privacy_guard/core/vault.py` | `VaultStore.session(id) / close_session(id)` | Per-session mappings; atomic files but concurrent collision behavior needs review |
| `privacy_guard/core/cipher.py` | `Cipher.encrypt/decrypt`; `default_cipher()` | Native OS encryption; only Windows adapter is implemented |
| `privacy_guard/claude_code/hook.py` | `run` / `handle` with injected journal, vaults and names | Event routing and handled-exception responses |
| `privacy_guard/claude_code/protection.py` | `protect_tool_output` / `restore_tool_input` | JSON string mapping and local-tool allowlist |
| `privacy_guard/claude_code/responses.py` | Response builders | Protocol serialization; shape-sensitive fallback needs correction |
| `privacy_guard/service/client.py` | `find_names`, `ensure_running`, `is_ready`, `stop` | Local process requests; sequential waits do not form a proven global deadline |
| `privacy_guard/service/channel.py` | Address and authentication key | Named pipe or Unix socket; same-user processes may read the key |
| `privacy_guard/service/server.py` | JSON byte requests and findings | Local inference; no pickle payloads; limits and stalled peers need review |
| `privacy_guard/journal.py` | `record(event, tool)` | Timestamp, event, tool name; no finding counters or restoration audit |
| `privacy_guard/claude_code/installer.py` | `install`, `status`, `uninstall` | Source deployment and settings registration; status checks registration, not runtime enforcement |

Prefer the existing seams for tests. Keep protocol fields inside the adapter and detection decisions inside the detector. Introduce a new interface when behavior actually varies or an enforcement responsibility needs its own owner; do not build a universal adapter SDK before a second adapter is understood.

## Proposed target

The [Archify target diagram](ux/privacy-target.html) focuses on incoming tool-result disclosure. The broader target contract below also covers restoration; neither describes today's complete enforcement:

- An agent adapter identifies content paths, validates schemas and requests inspection.
- The local privacy module detects and pseudonymizes; an OS-encrypted vault owns mappings.
- A protocol gate releases only a schema-valid transformed result on a covered path.
- A restoration policy authorizes a specific destination and operation before reading mappings.
- An execution control constrains files and network effects for restored values.
- A capability check and content-free journal report whether the covered-path contract is satisfied.

The model is outside the local trust boundary. Local tool execution is a separate trust decision: it may reach a network or external process. Unknown destinations must not receive restored values by default in the target contract.

## Adapter contract template

Every new adapter submission must state:

1. Agent version, platform, shell and event schemas tested.
2. Paths seen before disclosure: file tools, successful and failed shell output, MCP results, delegated tools, binaries/images, metadata, injected instructions and resumed context.
3. Whether transformation replaces original content or only adds context.
4. What happens when launch, parse, inference, encryption or delivery fails, including timeouts outside the handler.
5. How other hooks/plugins interact with transformations.
6. Authorized restoration destinations and protection against command injection, arbitrary writes and network egress.
7. How session identity, unknown tokens, concurrency and lifecycle are handled.
8. A synthetic real-agent compatibility suite and its evidence receipts.

An adapter can support a subset. Publish that subset; unsupported paths do not inherit a protection claim.

## Compatibility matrix

| Combination | Code present | Real model-boundary evidence | Release claim |
| --- | --- | --- | --- |
| Claude Code / native Windows | Yes; DPAPI vault and hooks | Not established in this groundwork | Prototype only |
| Claude Code / macOS or Linux | Some portable source; no default vault cipher | None | Unsupported |
| Claude Code / WSL with native Windows Python | Mixed-shell launcher failure observed in tests | None | Unsupported combination |
| Codex or another agent | No adapter | None | Future work |

For each future passing combination, record exact version, shell executable, configuration, fixture set hash, test mode, date and maintainer review. Use [adapter template](templates/adapter.md).

## External protocol evidence

Checked 2026-10-05 against the official [Claude Code hooks reference](https://code.claude.com/docs/en/hooks#posttooluse-decision-control): replacement output must match the tool schema; an invalid built-in replacement can leave original output in use. The [timeout contract](https://code.claude.com/docs/en/hooks#timeouts) also needs real-agent tests. These constraints motivate release blockers in the [baseline](security/baseline-2026-10-05.md).
