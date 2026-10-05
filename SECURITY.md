# Security policy

## Current status

Agent Privacy Guard is a research prototype. There is no supported public release or security certification. Current risks and checks are in [the baseline](docs/security/baseline-2026-10-05.md); requirements are in [the threat model](docs/security/threat-model.md).

## Reporting a vulnerability

**A private reporting channel is not configured yet.** Do not publish an exploit or private data in an ordinary issue or discussion. Do not include real credentials, original documents, vault contents or raw agent transcripts in a report.

Before a public repository opens, the maintainer must configure and test a private channel (such as repository private vulnerability reporting), replace this section with its actual route and assign a responder. This is a publication blocker. No email address or response-time guarantee is invented here.

When that channel exists, a useful report contains affected version/platform, synthetic reproducer, expected and observed behavior, which privacy invariant is affected, and sanitized evidence. A report does not need access to someone else's data to establish impact.

## Review and disclosure

Maintainers should acknowledge a report, reproduce it safely, determine affected versions, prepare regression evidence and a fix, and coordinate disclosure with the reporter. Response targets and supported-version windows must be selected before the first supported release.

Do not mark an issue fixed solely because unit tests pass. For agent protocol or enforcement flaws, include the applicable real-agent compatibility evidence. A security incident that may have exposed a live credential requires the credential owner's rotation/revocation process as well as a software fix.

## Evaluating safely

Use synthetic documents and test-only credentials. An installed hook or a status message is not proof of complete coverage. Do not rely on this prototype for real private files until the exact workflow has been reviewed and its limits accepted.
