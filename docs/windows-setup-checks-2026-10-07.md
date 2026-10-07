# Windows setup preview checks — 2026-10-07

Environment: native Windows 11 Home x64, build 10.0.26200. Builder Python 3.12;
packaged Python 3.14.8. This is a development machine, not a clean Windows VM.

The test-identity executable and normal executable use the same payload. Only
the application name, installation-directory name and uninstall-registry identity
differ. The normal identity has not been installed over the maintainer's active
configuration.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `PrivacyGuard-0.1.0-preview.1-windows-x64.exe` | 321572283 | `d51375fc4ee7318858342244c98c67f3df7590c60369627748903f9c56c71c29` |
| `PrivacyGuard-Test-0.1.0-preview.1-windows-x64.exe` | 321572358 | `e61d06915bd1283cd26285c6afcd6eabca4b9283b17ed5cb25d7fa50c0036a12` |

`tools/check_windows_setup.py` exercised the actual test executable with an
isolated profile and a path containing spaces and an accented character:

- Silent installation and bundled-runtime status check succeeded.
- DistilCamemBERT loaded through ONNX Runtime; the INSEE index was installed.
- Document names and e-mails were pseudonymized; Python-read e-mails were masked.
- Write restoration reproduced the synthetic source exactly; rereading reused tokens.
- Reinstallation preserved vault bytes, unrelated Claude settings and notification choices.
- Uninstall removed hooks and the packaged runtime, preserving unrelated settings and vaults.
- The real profile's sampled configuration fingerprints were unchanged.

The first reinstall attempt exposed a second concurrent model load exhausting
available memory. Setup now stops the previous detector before probing its
replacement; status checks reuse the installed service. The successful run also
revealed harmless console-decoding warnings in the test harness; it now captures
setup output as bytes, like NSIS output. These warnings did not bypass assertions.

The final full source suite ran 404 tests with no failures and two skips,
including nine setup tests. Local
Gitleaks scans found no secrets in the staged source export or packaged project code.

These checks use hook payloads, not an actual Claude Code model/network capture.
Clean-machine installation, actual VS Code/terminal sessions, older-version upgrade
testing and Authenticode signing remain pending. No stable product claim follows
from these checks. See the [installation guide](windows-installation.md).
