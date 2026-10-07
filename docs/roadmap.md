# Roadmap and contribution lanes

Milestones have exit criteria, not promised dates. Security tasks are local in [.scratch/security-baseline](../.scratch/security-baseline/spec.md).

Progress on 2026-10-05: the source is published under MIT and the three published commits have been scanned. Selecting Git Bash produced 124 passing tests and one optional-model skip; automatic shell selection and real-agent enforcement remain open. The private vulnerability-reporting channel is still pending. See the [history audit](security/history-audit-2026-10-05.md) for these checks and the [project assessment](project-assessment.md) for the proposed first workflow. The immediate priority remains M1, followed by M2; publication has not closed the security gates for M3.

## M0 — Reproducible foundation

Update on 2026-10-06: the selected DistilCamemBERT is integrated, exact-text detection caching and transactional DPAPI-encrypted vault storage are deployed, and CPU window batching was evaluated and rejected. Handled post-tool failures now request a native stop and recognized result replacements; native user notices and sensitive-error stopping are deployed. Notices now include category occurrence counts and document basenames, with a local metadata summary journal. The suite runs 296 tests with no failures and two skips. M1 still requires actual model-boundary and hook-absence/timeout evidence; local emission checks do not close those gates. See the [current architecture and receipts](architecture.md#handled-failures-and-native-user-notices).

Deliver: supported scope and exclusions, source map, glossary, threat model, UX simulation, contribution templates and a local backlog.

Exit: documentation links and prototypes checked; maintainers can reproduce the baseline and explain all gaps; license and reporting-channel choices are recorded for the publication milestone.

## M1 — Verified Claude Code integration

Deliver: one tested native Windows/shell/agent combination, schema-correct failures, explicit unknown-path behavior and compatibility receipts.

Exit: SEC-01 and SEC-03 resolved with synthetic real-agent evidence; installation tests pass in the declared combination; timeouts and launch failures cannot silently release originals on claimed covered paths. If the hook mechanism cannot satisfy the gate, redesign or narrow the claim.

## M2 — Safe local restoration

Deliver: destination and operation policy, explicit secret handling, protected local document output and denied network/delegation cases.

Exit: SEC-02 resolved; local-tool arguments cannot be used to turn tokens into uncontrolled disclosure or executable shell syntax; cross-session and unknown-token behavior is documented and tested.

## M3 — Community alpha

Deliver: stable synthetic corpus, separate model-enabled/heuristic results, usable diagnostics, license, vulnerability channel, sanitized repository and review rules.

Exit: SEC-04, SEC-05 and publication task reviewed; no unresolved release-blocking issue; fresh-clone tests and independent review; publish only the compatibility claims demonstrated. Gather pilot feedback before calling it stable.

## M4 — Additional platforms and agents

Deliver one adapter or native cipher at a time. Exit per integration: equivalent compatibility evidence, covered-path list, model-mode results and recovery behavior. Codex is a candidate, not an announced supported integration.

## M5 — Commercial validation

Test installation and support with trial users, and record whether they continue using the tool. Exit: maintenance costs, user willingness to pay and community impact reviewed. Commercial wrappers must not remove essential fixes from the core.

## Contribution lanes

| Lane | Good first contribution | Completion evidence |
| --- | --- | --- |
| Documentation | Clarify one flow or misleading status phrase | Cross-check against code and glossary |
| Detection | A synthetic missed/false-positive fixture | Per-category before/after scores in a declared mode |
| UX | Improve degraded/failure comprehension | Scenario script and anonymized usability observations |
| Security testing | One malformed structured output case | Handler test plus real-agent harness plan |
| Installation | Reproduce shell-path incompatibility | Versioned platform/shell receipt in temp directories |
| Adapter research | Map one vendor's supported interception points | Primary docs, coverage list and unknowns |

Security enforcement and restoration tasks need maintainer involvement; they are not starter tickets for unreviewed automated changes. A task is small enough when its outcome can be demonstrated at one existing interface.
