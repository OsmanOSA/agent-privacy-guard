# Project context

Agent Privacy Guard exists because instructions asking an agent to avoid private documents are not an enforceable privacy control. The user should be able to delegate useful work without providing unnecessary personal values to a remote model.

## Decisions already made

- Start with Claude Code. A narrow integration makes it possible to study actual behavior before multiplying adapters.
- Keep detection and reversible mappings local. Pseudonymization preserves relationships needed for reasoning.
- Restore values only at an authorized local destination. The model's textual reply is not automatically restored by today's implementation.
- Keep the hook on the Python standard library; optional name inference lives in a separate local process.
- Encrypt persisted mappings with the operating system's cipher. Today that means native Windows DPAPI.
- Publish reviewed source under MIT; keep private captures and runtime data local. The repository is now on GitHub. The initial baseline's absence of Git history is retained as a dated observation.
- Write contributor-facing material in English; retain the French vision PRD with a scope notice.

## Evidence and aspirations

On explicit user request, the 2026-10-07 global Windows upgrade deployed the reviewed name-consistency fixes, within-session encrypted name reuse, content-free failure diagnostics and the official INSEE lexicon. Existing vault files and Claude settings were preserved. Installed native hook probes verified lowercase personal fields, cross-call recognition, session separation and local restoration. The [upgrade evidence](docs/architecture.md#global-upgrade-2026-10-07) does not establish an actual agent/model network boundary.

Optional Windows desktop notifications use count-only per-session grouping, verified window ownership and detached delivery. The user selected a dark Driftlight-inspired card. On 2026-10-07 the completed Windows presentation was deployed globally and enabled in background mode, preserving the two existing vault files, Claude settings and model/export configuration. The card prepares hidden, rechecks focus and quiet state before display, selects the host monitor and can return to a verified host window. Quiet-profile discovery uses an undocumented read-only Windows adapter; unknown state falls back to native delivery. New installations still default to off. Exact editor-tab/terminal-pane identity remains unsupported. See [notification architecture and checks](docs/architecture.md#optional-windows-desktop-notifications-2026-10-07) and [.scratch/notification-finish/deployment.json](.scratch/notification-finish/deployment.json).

Subsequent user feedback exposed a real rendering defect: the card's native window
was only 2 pixels high even though WPF reported ContentRendered. Content is now
measured before hidden-window creation; native dimensions are checked. The user
confirmed seeing the corrected 412 x 242 card. External numbered placeholders
such as PERSON_001 and [EMAIL_001] also remain literal, even if an old vault
mapping learned them as names. Adjacent real personal values and secrets remain
protected. The 395-test suite passes with two existing skips; benchmark scores
are unchanged in heuristic and model modes. Both fixes were deployed globally,
preserving existing vaults and settings. Latest receipts are in
`.scratch/notification-markers/`. Automatic restoration of source-code files is
still unsupported.

The core, adapter and tests exist. End-to-end interception across a real agent/model boundary has not been demonstrated in this work. Ordinary user-level hooks can be disabled or changed and do not provide operating-system isolation. The intended mandatory inspection contract requires a path-by-path compatibility suite and additional enforcement where hooks alone are insufficient.

The authoritative reading order is product brief → threat model → architecture → roadmap. The glossary defines product language, not code details. ADRs record costly decisions, not every implementation choice.

## Decisions still open

1. Enforcement mechanism for shell/network effects and hook failures.
2. Which destinations can receive restored personal data, and whether any secret can be restored at all.
3. Required behavior when the name model is unavailable.
4. MIT attribution; model/tokenizer/data redistribution rights; commercial offering.
5. Vulnerability-reporting channel and first public maintainers.
6. First supported Claude Code version and tested shell/platform combination.

Use the [local backlog](.scratch/security-baseline/spec.md) to resolve these questions with synthetic evidence. No task is permission to send real data, publish, install into a user's live agent, or edit unrelated files.
