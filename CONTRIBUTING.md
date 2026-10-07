# Contributing

Before proposing a change, read the [product brief](docs/product.md), [glossary](GLOSSARY.md) and [threat model](docs/security/threat-model.md). Today the focus is Claude Code; expanding to other agents is planned work.

## Before making a change

1. Find a local work item in `.scratch/`, or draft one with [the spec template](docs/templates/spec.md).
2. Describe the user-visible problem and a synthetic reproducer. Never paste personal files, real keys, raw session transcripts or vault mappings.
3. Identify the existing interface to test and the security invariants affected.
4. Agree scope in the work item. For a new adapter or restoration change, use its template and identify a maintainer reviewer.

No external tracker is configured yet. Templates in `.github/` are preparation for a future repository and do not create issues or PRs.

## Development

Baseline: Python 3.12. The hook and core use the standard library. Optional ONNX name inference has its own environment; model building is separate from runtime development.

```powershell
python -m unittest discover -s tests -t .
python -m benchmark --spaced
```

Tests use temporary directories. The Windows suite on 2026-10-07 has 395 tests with no failures and two skips (optional model and unavailable symlink creation). The earlier shell-launch failures are recorded in [the historical baseline](docs/security/baseline-2026-10-05.md). Preserve a failing baseline in the change evidence; do not silently skip a failing supported-platform check.

Keep synthetic Stripe keys compatible with push protection: assemble full-length keys from separate string literals in Python (see `tests/fakes.py`). Static corpus examples use a 16-character suffix, the detector's minimum, instead of a full-length credential-shaped value. Adding `FAKE` alone does not prevent a source scanner from flagging a key.

Before pushing, scan the complete history with Gitleaks and the repository's configuration. See the [history audit](docs/security/history-audit-2026-10-05.md) for the command and the four reviewed false positives. Any new exception must identify the exact synthetic value and its file; keep the default detection rules enabled.

For detection changes, run before and after with the **same corpus and mode**, add a synthetic fixture first, and compare category recall and precision. The benchmark's successful exit code alone does not gate metric regressions. Record its scores and review any drop explicitly.

For model-enabled evaluation, use the model environment's Python. `--spaced` exists because the corpus is synthetic and guard hooks may transform displayed values; it is never a technique for printing real private data. Model build/validation scripts require their dedicated build dependencies and are not part of a routine docs change.

## Code standard

- Use English for code, comments, messages and contributor documents.
- One function has one task. A module should have one clear responsibility and a small interface.
- Aim below 200 lines per module; split mixed responsibilities. Never introduce a 1,000-line module.
- Explain constraints and non-obvious choices in comments; open runtime modules with a role/interface docstring.
- Inject journal, vault, detector and platform dependencies where behavior varies.
- Test externally visible behavior at existing interfaces, including error outcomes. A JSON builder assertion alone is not agent compatibility evidence.
- Keep protocol details in the adapter, detection rules in the core and cipher details in native cipher adapters.
- No home-made encryption, inspected-content telemetry or hidden network calls.

## Installation is a separate action

Running source tests does not redeploy the installed hook. `python -m privacy_guard install` writes to user directories and Claude Code settings and may fetch the name model. Compatible updates preserve session vaults; an unknown or incompatible vault format stops installation without deleting them. Uninstall deletes the vaults. Run installation only when explicitly working on it and after passing the relevant checks in the supported shell combination.

The vault format contract is recorded in `vault-format.json` outside the deployed app. Bump `CURRENT_FORMAT` in `claude_code/vault_format.py` whenever the encrypted record layout, token derivation or cipher changes. An unmarked existing installation can be adopted only when its format-related core sources exactly match the incoming package. No automatic migration or destructive reset is included.

The v2 engine reads v1 encrypted files and stores new bound records as DPAPI-encrypted SQLite BLOBs. Keep legacy records authoritative and commit new mappings before returning tokens. SQLite metadata remains visible; do not put plaintext values into database fields, diagnostics or receipts. Cover transaction failures, concurrent collisions and unchanged legacy bytes when changing this storage contract.

Use temporary `--claude-dir` and `--guard-home` paths for installation tests. The current source still uses default runtime locations in several places: temporary install flags alone are not proof of complete runtime isolation. Prefer the existing tests until path isolation is verified.

Removal from an independent terminal is `python -m privacy_guard uninstall`; it removes the guard and its vaults, while logs and configuration backups may remain. Preserve recovery evidence and do not run install/uninstall against another person's environment.

## Review and completion

A change is ready when its scoped behavior is demonstrated, relevant checks are recorded, known failures/skips are explained, security implications are reviewed and related docs remain consistent. For code changing disclosure or restoration, update the compatibility matrix and add model-boundary evidence when needed.

Two-person review for security-sensitive changes is the target once a second maintainer exists. Until then, do not describe a single-maintainer review as independent auditing; public alpha readiness requires an independent reviewer.

Contributions to project code use the [MIT License](LICENSE). Use [PR template](.github/pull_request_template.md) and [release guide](docs/releasing.md). No commit, push, deployment or publication is implied by contributing a local draft. External contributions should open only after a private vulnerability channel exists.
