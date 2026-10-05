# Publication and release guide

Status: a local preparation procedure. It creates neither a repository nor a release. No history exists in this workspace at the initial baseline; there is no existing GitHub history to audit here.

## Gate A — Open a public source repository

Before publication, a maintainer records evidence for each item:

- [ ] Select the project license and add the exact license text, notices and contribution terms.
- [ ] Verify runtime/build dependency, model, tokenizer and dataset provenance and redistribution rights. The existing generated model card is an input to review, not completed legal verification.
- [ ] Establish a private vulnerability-reporting route and a conduct contact; update SECURITY.md and CODE_OF_CONDUCT.md.
- [ ] Make the README state prototype status, supported scope and known gaps. Public source may precede a stable product only with those limits prominent.
- [ ] Prepare a clean export **outside any runtime vault/model/log directories**, from an explicit path allowlist; review each included fixture.
- [ ] Inspect all included files with a secret scanner and a private-data review. Never send the tree to a hosted scanner without explicit authorization.
- [ ] Remove local credentials, config backups, private captures, personal paths, model weights and unsanitized transcripts from the export. An ignore rule is not a content scan and does not remove a tracked file.
- [ ] Review `playground/.env`: it is described as synthetic but ignored by default. Publish only a sanitized example or separately reviewed fixture, not a blanket `.env` exception.
- [ ] Verify all archived examples are synthetic; maintain a fixture provenance record. For token-shaped dummy values, use narrowly documented scan exceptions, never a global disabled rule.
- [ ] Re-run checks from the exact clean export; record failures, skips and modes. Label unresolved findings publicly at a safe level.
- [ ] Inspect the exact initial commit and its file list locally before any remote is added or pushed. Use only reviewed project files; avoid an indiscriminate initial `git add .`.

A source-publication checklist does not waive product-release blockers. If the initial prototype is made public with known gaps, it must remain explicitly unsuitable for sensitive production use.

## Keeping the first history understandable

Keep the current working folder as the development source. Create a reviewed export and initialize its repository only when publication is authorized. The initial commit should explain the prototype, scope and baseline. Subsequent commits should describe one coherent change with associated evidence.

Do not fabricate past versions, scrub another contributor's attribution, rewrite a shared history or force-push to make it look clean. If credentials have ever been committed, rotate them first; plan coordinated history remediation separately. If an existing remote/history is introduced later, audit all reachable history as well as the current tree.

For a future Git repository, useful read-only checks include `git status --short`, `git diff --cached --stat` and `git ls-files`. [Gitleaks](https://github.com/gitleaks/gitleaks) provides local directory and Git-history scan modes; pin the tool version, follow its current CLI, redact findings, and keep reports private. Secret detection does not certify absence of personal data.

## Gate B — Ship an installable alpha

- [ ] Close the applicable P0 enforcement/restoration/coverage tasks with real-agent evidence.
- [ ] Declare exact agent/platform/shell versions and unsupported paths.
- [ ] Pass installation, repair, removal and configuration-preservation checks on the supported combination.
- [ ] Publish separate heuristic and model-enabled benchmark receipts, corpus identity and known misses.
- [ ] Demonstrate required failure behavior, concurrency, tampering response and destination restrictions.
- [ ] Have an independent security reviewer assess the claims and unresolved risks.
- [ ] Produce artifact checksums, dependency inventory, provenance and an update/rollback strategy.
- [ ] Record whether model weights are separate artifacts and how a user verifies their hashes and attribution.
- [ ] Validate fresh-clone setup using synthetic data with no developer home-directory assumptions.
- [ ] Review release notes and UX status language against the actual evidence.

## Gate C — Release record

Use [the release template](templates/release.md). Record source revision only once a real commit exists; record exact artifact hashes, runtime/model versions, commands, results, reviewer and support window. Do not reuse benchmark scores from a different build or claim a skipped model test passed.

After release, a supported-version failure should change the compatibility status and trigger an advisory through the configured channel. Do not silently maintain a green badge while a covered path is known to leak.
