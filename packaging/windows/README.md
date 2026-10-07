# Building the Windows setup

Run on Windows with a builder Python 3.12 or newer. The builder does not install
into the current Claude Code profile. Build files and downloads stay in ignored directories.

## Inputs

- `dependencies.lock.json`: exact Python, NSIS and wheel downloads, SHA-256 digests
  and package license metadata.
- A model bundle from `tools/prepare_distil_bundle.py`, checked against
  `privacy_guard/service/distil_files.py`.
- An optional public INSEE index from `tools/prepare_insee_lexicon.py`, its
  `.source.json` receipt and the repository's attribution notice.
- Project Python source and license. No vaults, logs, developer environment,
  credentials or test corpus are copied.

Python 3.14.8, ONNX Runtime 1.30.0, NumPy 2.5.3 and tokenizers 0.22.2 are pinned.
NSIS 3.12 uses its zlib compressor. No network is needed during end-user installation.
Dependency license files remain alongside their packages, with Python's license,
the model's upstream card and INSEE provenance. They retain their respective licenses;
the project's MIT license does not replace them.

## Build and check

```powershell
python tools/build_windows_setup.py --model release/distilcamembert-ner --lexicon evaluation/ner/data/insee/data/insee-names.sqlite --work .local-review/windows-setup/build-preview --test-build
python tools/check_windows_setup.py dist/PrivacyGuard-Test-0.1.0-preview.1-windows-x64.exe --work .local-review/windows-setup/smoke-preview
python -m unittest discover -s tests -t .
```

Use a new `--work` directory each time. `--test-build` uses separate application,
Start menu and HKCU uninstall-registry identities; omit it for the normal installer.
`--version` defaults to `0.1.0-preview.1`. Never change a published payload under
the same version. Downloads are verified before extraction, and `payload.json`
inventories packaged file hashes. The `.exe.sha256` is not a publisher signature.

The setup check requires an INSEE-equipped test build. It creates a temporary
profile, invokes the actual installer, runs packaged hooks and the model, restores
and rereads a document, reinstalls and uninstalls. It checks vault bytes, preferences,
unrelated Claude settings and real-profile fingerprints. The separate test product's
registry entry and shortcuts are removed by its uninstaller. Fixtures are synthetic.

Unit tests cover rollback, concurrent locks, corrupted payloads, disabled hooks,
uninstaller ownership and interpreter selection. Neither suite proves what a real
Claude Code process sends over the network.

## Before publishing

Record the source commit, artifact SHA-256, Windows/Claude/shell versions and checks
in the [release record](../../docs/templates/release.md). Test on a clean Windows
VM/account: native libraries on the development machine can hide missing DLLs.
Test upgrades from an older installer, sign the executable, verify the signature
and regenerate its checksum. There is no automatic updater in this preview.

Sources: [Python releases](https://www.python.org/downloads/windows/),
[Python 3.14.8 hashes](https://www.python.org/ftp/python/3.14.8/windows-3.14.8.json),
[NSIS](https://nsis.sourceforge.io/Download),
[NSIS license](https://nsis.sourceforge.io/Docs/AppendixI.html),
[Claude Code settings](https://code.claude.com/docs/en/settings).
