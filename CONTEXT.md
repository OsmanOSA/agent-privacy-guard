# Project context

Agent Privacy Guard exists because instructions asking an agent to avoid private documents are not an enforceable privacy control. The user should be able to delegate useful work without providing unnecessary personal values to a remote model.

## Decisions already made

- Start with Claude Code. A narrow integration makes it possible to study actual behavior before multiplying adapters.
- Keep detection and reversible mappings local. Pseudonymization preserves relationships needed for reasoning.
- Restore values only at an authorized local destination. The model's textual reply is not automatically restored by today's implementation.
- Keep the hook on the Python standard library; optional name inference lives in a separate local process.
- Encrypt persisted mappings with the operating system's cipher. Today that means native Windows DPAPI.
- Prepare documentation and work items locally. There is no Git repository in this workspace at the initial baseline; no history or remote has been created.
- Write contributor-facing material in English; retain the French vision PRD with a scope notice.

## Evidence and aspirations

The core, adapter and tests exist. End-to-end interception across a real agent/model boundary has not been demonstrated in this work. Ordinary user-level hooks can be disabled or changed and do not provide operating-system isolation. The intended mandatory inspection contract requires a path-by-path compatibility suite and additional enforcement where hooks alone are insufficient.

The authoritative reading order is product brief → threat model → architecture → roadmap. The glossary defines product language, not code details. ADRs record costly decisions, not every implementation choice.

## Decisions still open

1. Enforcement mechanism for shell/network effects and hook failures.
2. Which destinations can receive restored personal data, and whether any secret can be restored at all.
3. Required behavior when the name model is unavailable.
4. Project license; model/tokenizer/data redistribution rights; commercial offering.
5. Vulnerability-reporting channel and first public maintainers.
6. First supported Claude Code version and tested shell/platform combination.

Use the [local backlog](.scratch/security-baseline/spec.md) to resolve these questions with synthetic evidence. No task is permission to send real data, publish, install into a user's live agent, or edit unrelated files.
