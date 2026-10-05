# Verified Claude Code privacy contract

Status: open

## Problem

The founder needs a privacy control applied independently of agent instructions. The current prototype pseudonymizes detected result strings, but mandatory inspection, safe restoration and honest capability status are not yet demonstrated across the actual agent boundary.

## Outcome

One explicitly supported Claude Code/platform/shell combination with tested covered paths, authorized local restoration and reproducible failure behavior. Publish source only with the separate publication gate; do not advertise verified protection before evidence exists.

## Existing test seams

Use the injected hook handler, PrivacyCore, vault and cipher interfaces for regressions. Add an instrumented real-agent model-boundary harness for protocol/enforcement evidence; a fake response consumer cannot establish the real agent contract. A destination policy interface is proposed and needs design review before implementation.

## Work items

| ID | Task | Priority |
| --- | --- | --- |
| SEC-01 | [Protocol and enforcement](issues/01-protocol-enforcement.md) | P0 |
| SEC-02 | [Restoration policy](issues/02-restoration-policy.md) | P0 |
| SEC-03 | [Coverage contract](issues/03-coverage-contract.md) | P0 |
| SEC-04 | [Capabilities and installation](issues/04-capability-and-installation.md) | P1 |
| SEC-05 | [Vault, service and journal](issues/05-vault-service-journal.md) | P1 |
| REL-01 | [Publication readiness](issues/06-publication-readiness.md) | Publication gate |

## Out of scope

Additional agent adapters, new platforms, live-user data tests, automatic installation, public GitHub creation, pricing commitments and telemetry services. Product ambitions remain in the roadmap.
