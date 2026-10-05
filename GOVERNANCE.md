# Governance

Status: proposed community operating model. The project founder owns decisions during local preparation. Named maintainers and contacts will be recorded before opening contributions; this document does not invent a committee or assign individuals.

## Roles

- **Contributor:** proposes a bounded change with synthetic evidence.
- **Maintainer:** reviews scope, compatibility and code quality; can accept changes after documented review.
- **Security reviewer:** examines disclosure/restoration invariants and release blockers. Independent review is required for the first public alpha security claim.
- **Release steward:** checks the exact source/artifact pair, license inventory, security-reporting readiness and release evidence.

One person can hold multiple roles in preparation. Record when a review is not independent. Add maintainers based on sustained contributions and judgment, with scope and access documented.

## Decisions and disagreements

Discuss routine changes in their work item. Durable architectural trade-offs use a concise ADR. The founder resolves unresolved local-preparation decisions and records the reason; community governance can evolve when multiple maintainers exist.

Security claims need evidence, not a vote. An unresolved release blocker prevents the corresponding claim or release. Disagreement about evidence is recorded with a reproducer and reviewed by someone who did not implement the change when possible.

## Open source and commercial work

The intention is a community-developed privacy core with possible paid distribution, UX, integration maintenance and support. No commercial entitlement, pricing or closed component is established by this document. Keep decisions about the core's essential behavior and security fixes explicit.

Project code and contributions use the [MIT License](LICENSE). Model, tokenizer, dataset and other third-party redistribution terms must be checked separately before distributing those assets. Introducing a CLA or DCO requires an explicit project decision.

## Community stewardship

Apply the [code of conduct](CODE_OF_CONDUCT.md). Establish a private reporting contact and an escalation route before operating public discussion channels. Security reports use [SECURITY.md](SECURITY.md), not ordinary issue forms.
