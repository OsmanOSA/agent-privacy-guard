# Git history audit — 2026-10-05

The audit covered all reachable Git branches and tags and the tracked source tree. GitHub advertised only `main`, with no tags. Before the audit commit, the published history contained `0440adf` (initial source) and `626c27f` (MIT license).

## Secret scan

Gitleaks v8.30.1 was downloaded from its official GitHub release. The Windows archive's SHA-256 matched the release checksum file. Reports were redacted and retained locally under `.local-review/`, which is ignored by Git.

The default rules reported four findings. Each was reviewed at its source:

| File | Finding | Review |
| --- | --- | --- |
| `tests/test_secret_detector.py` | JSON API key example | Synthetic assignment-detector fixture: `abcd1234efgh`. |
| `tests/test_secret_detector.py` | URL query token example | Synthetic assignment-detector fixture: `a1b2c3d4e5f6`. |
| `tests/test_secret_detector.py` | French password example | Synthetic assignment-detector fixture: `Lyon-2026-secret`. |
| `privacy_guard/service/model_files.py` | Tokenizer manifest entry | A pinned SHA-256 file digest, used to verify the model assets. |

[`.gitleaks.toml`](../../.gitleaks.toml) retains every default rule. Its exceptions require both the exact reviewed value and the corresponding file path, and apply only to `generic-api-key`. There is no blanket exception for tests, commits, secret types or high-entropy values. The complete reachable history passed with these exceptions, including archive inspection and decoding to a depth of two.

Synthetic probe values confirmed that new values in both exception files, and an allowed fixture value in an unrelated file, are still detected.

Provider-shaped synthetic inputs remain in the detection tests and benchmark. The Python Stripe fixture is assembled from separate literals; the static Stripe examples have a 16-character suffix. These are test data, not operational credentials. A passing scan does not prove that every possible secret format is absent.

## File review

Every reachable commit was checked for private artifacts: environment files other than the reviewed example, vaults, runtime settings, model weights, executable archives, Python caches and local review captures. None were tracked.

The home-directory paths in `benchmark/corpus/traceback.log`, `tests/test_document_scope.py` and `tests/test_registration.py` are synthetic examples (`dev`, `me` and `user`). A local username in the name-filter test was replaced with `devuser`.

`CLAUDE.md` is now ignored and removed from the current Git index; the local file is preserved. Earlier published commits still contain it. It contains development instructions, not credentials, so their history is retained. The README's current link to that local-only file was removed.

The originally rejected commit, `4e160194da1faac71490f9c96d1b8ac3fe59c614`, is not reachable from any advertised GitHub ref. GitHub's commit endpoint returned HTTP 422 for that identifier during the audit. Local recovery data is outside the published refs.

## Reproduce

With Gitleaks v8.30.1, from the project root:

```powershell
gitleaks git . --log-opts="--all" --config .gitleaks.toml --max-decode-depth=2 --max-archive-depth=2 --redact
```

For a clean source export, retain `.gitleaks.toml` and scan that directory with `gitleaks dir` using the same configuration and depth flags. Do not scan ignored local runtime data as though it were part of the public source export.

The Windows test run used Git Bash first on the process PATH: 125 tests, 124 passed and one optional-model test skipped. No live hook installation was changed.
