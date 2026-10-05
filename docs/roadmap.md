# Roadmap and contribution lanes

Milestones have exit criteria, not promised dates. Security tasks are local in [.scratch/security-baseline](../.scratch/security-baseline/spec.md). No milestone is currently marked complete merely because its documents exist.

## M0 — Reproducible foundation

Deliver: honest product scope, source map, glossary, threat model, UX simulation, contribution templates and a local backlog.

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

Deliver a tested onboarding/support proposition and measured pilot demand. Exit: maintenance costs, user willingness to pay and community impact reviewed. Commercial wrappers must not remove essential fixes from the core.

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
