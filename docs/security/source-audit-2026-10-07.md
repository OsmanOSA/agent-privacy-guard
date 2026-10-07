# Source publication check — 2026-10-07

This update publishes the accumulated local privacy, restoration, French NER
evaluation and Windows-notification work. It is a source update, not a claim of
stable product certification. Existing public history is preserved.

## Export and test evidence

An explicit staged-file export was tested independently of ignored developer
files: 395 tests, zero failures/errors, two existing skips (optional ONNX model
and unavailable Windows symlink creation). An initial clean-export run exposed
four tests that depended on `playground/.env`; those now use a checked-in
synthetic Python fixture. No private `.env` was copied into the repository.

The final fixture representation was checked with the 18 relevant detector tests
again. The recent detector changes also retain identical reference-corpus scores
and findings before/after in both heuristic and DistilCamemBERT modes. See
`.scratch/notification-markers/` for the detection and notification evidence.

Dataset downloads, per-record evaluation results, model weights, runtime vaults,
credentials, caches and local-review captures are excluded. Evaluation source,
provenance records and aggregate metrics are included. Three notification upgrade
receipts now use `~/.privacy-guard` paths; their original local copies were retained
outside Git. The installed-hook probe no longer hard-codes a developer username.
Required license attribution remains intact.

## Secret scan

The locally verified Gitleaks 8.30.1 binary scans the staged source export and all
reachable history with the repository configuration, decoding and archive depth
two, and redacted reports. The reviewed source scan reports no leaks.

The first source scan reported 18 generic-key matches in SHA-256 metadata:
tokenizer manifests and evaluation records of source/artifact hashes. Inspection
confirmed all 18 were 64-character file digests. Nine additional allowlist entries
in `.gitleaks.toml` require the exact reviewed digest **and** its specific file
path. Default detection rules remain enabled. There is no global hash, test-folder,
evaluation-folder or commit exclusion. New synthetic credentials in two allowed
files and a reviewed digest in an unrelated file were all detected by three
isolated scanner probes.

The synthetic environment JWT is assembled separately from its assignment label,
like the existing synthetic Stripe fixture. This needs no new scanner exception.
Private scanner reports and exports stay in `.local-review/publish-20261007/`.
The earlier [history audit](history-audit-2026-10-05.md) documents the existing
fixtures and their narrow exceptions. A passing scan does not guarantee the
absence of every possible secret or personal-data format.
