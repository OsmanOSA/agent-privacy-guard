# REL-01 — Prepare a reviewed public source tree

Status: open
Priority: publication gate
Blocked by: none

## Outcome

A local clean export with a selected license, attribution inventory, reporting contacts, reviewed fixtures and reproducible baseline. Public alpha packaging additionally depends on SEC-01 through SEC-05.

## Acceptance

- Complete Gate A in docs/releasing.md; keep prototype limits prominent if publishing source before product readiness.
- Review the synthetic playground `.env`, logs, examples and token-shaped values; narrow scanner exceptions only.
- Run local secret scanning and a personal-data review; redact findings and record tool/version/scope.
- Verify fresh-copy setup without local service/model/home assumptions.
- Create a real initial Git commit only when requested; inspect its exact contents before remote creation or pushing.
- Establish private vulnerability and conduct routes before external contributions.

## Comments

This work item does not authorize publishing or creating a GitHub repository.
