# Product brief

Status: published research prototype under MIT, 2026-10-05. This document defines the intended delivery scope, not a certification of the prototype. The [project assessment](project-assessment.md) records current evidence and proposes the next validation work.

## Problem and intended outcome

An agent with file and shell access can discover personal data while doing a legitimate development task. A prompt asking it not to read personal documents does not show whether it complied. Users need a control applied by the surrounding software, independently of the agent's willingness to follow that prompt.

Agent Privacy Guard aims to inspect every **covered path**, replace detected sensitive values before they enter model context, and restore needed originals at an authorized local output. The rest of a useful document may still reach the model. A detector can miss data, so this goal does not imply anonymization or zero disclosure.

## First delivery

| Area | Current implementation | First validated delivery |
| --- | --- | --- |
| Agent | Claude Code hooks | One pinned Claude Code version and documented tested tool set |
| Platform | Native Windows vault cipher | One tested native Windows + shell combination |
| Incoming content | String values nested in successful tool results | Each supported schema and failure path verified at the agent boundary |
| Detection | Rules and heuristic names; optional local ONNX names | Published corpus mode, per-category scores and known misses |
| Restoration | Tokens in selected local tool arguments | Explicit destination policy, session binding and no uncontrolled egress |
| Status | Hook configuration and model-file readiness | Capability checks and actual compatibility evidence |
| User experience | Install/status/uninstall CLI | Honest setup, degraded-mode and failure feedback |

Codex and other companies' agents are part of the long-term direction. Adding them requires an adapter with equivalent evidence. Neither vendor nor platform support follows automatically from a reusable core.

## User stories

1. As a developer, I can understand which agent, platform and paths are supported before installation.
2. As a user, I can analyze a synthetic document while personal values are represented consistently by tokens.
3. As a user, I can produce a local document with restored originals without sending originals back into model context.
4. As a user, I can distinguish installed hooks from a verified protected session.
5. As a user, I receive a visible failure when required inspection cannot complete.
6. As a user, I can see when name detection is reduced and choose whether to stop the covered workflow.
7. As a user, I can inspect content-free events without exporting my documents or mappings.
8. As a contributor, I can reproduce a detector miss with a synthetic fixture.
9. As an adapter author, I can reuse core behavior while documenting my agent's coverage and exclusions.
10. As a maintainer, I can reproduce a release from a reviewed source tree without embedding local vaults, logs or credentials.

## Mandatory inspection means a contract

For a supported path, inspection must run before model disclosure; a required inspection failure must not silently release original content. Configuration tampering, timeouts, process launch errors, unsupported outputs and competing hooks must all have tested behavior. If the platform cannot enforce this, the UI reports that limitation and the path does not qualify as covered.

Preventing an agent from opening a file is a separate access-control capability. This prototype mainly transforms results after local reads; it does not stop the read itself. Network side effects need controls before execution. A local shell is not automatically an authorized restoration destination.

## First delivery acceptance

- Use a synthetic canary corpus in a real supported agent session. Observe an instrumented model boundary through a controlled test harness; inspect outbound content locally. Store only pass/fail, fixture identifiers and environment versions in shared evidence.
- Every covered path has success, malformed-input, failure, timeout and concurrent-call evidence. Unknown paths have an explicit outcome.
- Every restoration path has authorized-output, denied-destination, cross-session, unknown-token and malicious-command evidence.
- Heuristic and model-enabled scores are separate. Detection regressions require an explicit review and new fixtures.
- Installation, repair and removal preserve user configuration and have recovery evidence.
- Public claims match the compatibility matrix and security baseline.

## Beyond the first delivery

Future directions: enforceable network and filesystem policy, a reviewed restoration broker, additional native ciphers, signed desktop distribution, more adapters, richer content extraction and optional organization controls. OCR, raw binary documents and image payloads need separate extraction and coverage tests.

User-typed prompts, previous conversation history, external integrations and arbitrary process activity are outside today's implementation. Direct restoration of the chat answer is also absent. A local file written by a selected tool can be restored; that distinction belongs in the onboarding experience.

## Prospects and validation

Assessment: this is worth testing because the pain is concrete and the local core is already present. The differentiator must be measured agent integration, safe restoration and clear operational status. Community contributions become useful when a synthetic fixture can turn an observation into a reproducible rule or adapter test.

Detection alone is an established capability: [Presidio](https://presidio.dataprivacystack.org/) is a reference to compare against. [Claude Code sandboxing](https://code.claude.com/docs/en/sandboxing) addresses shell filesystem/network restrictions, with its own tool and platform limits. Those are adjacent capabilities, not proof that this integration works. The product opportunity is an inference, not demonstrated demand.

Proposed discovery targets, not current results: interview 10 developers about a recent privacy incident or avoidance behavior; have 5 independently run a synthetic trial; observe at least 3 willing to keep using it after a week. Ask what they would pay for and compare onboarding time, blocked work and support effort. Revise these thresholds after the first cohort.

Potential commercial value: maintained integrations, desktop setup, signed delivery and support. Keep essential privacy behavior, vulnerability fixes and honest limitations available to the community. Prices and one-time versus recurring payment in the older PRD are hypotheses; ongoing vendor compatibility creates ongoing cost. Do not commit to lifetime maintenance before measuring that cost.
