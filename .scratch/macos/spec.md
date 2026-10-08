# macOS port

Branch `feat/macos`, cut from `fix/model-boundary-leaks` at f46a4f0 (Windows
0.1.0-preview.5). One codebase: every macOS difference lives behind the same
platform seams Windows already uses, selected by `sys.platform`. The Windows
behaviour and its tests stay unchanged; the full suite must stay green on
Windows after each step.

## Seams found in the Windows build

| Seam | Windows today | macOS work |
| --- | --- | --- |
| Vault cipher (`core/cipher.py`) | DPAPI via ctypes | Random key in the login Keychain (Security.framework via ctypes), AES-256 from CommonCrypto with an HMAC-SHA256 tag (encrypt-then-MAC). Raises today. |
| Restored and exported writes (`exports/windows_files.py`, `written_file_handles.py`) | Pinned native handles, reparse-point and hard-link refusal | POSIX equivalent: `O_NOFOLLOW`, `openat`-style directory pinning, `st_nlink`, regular-file and local-volume checks. |
| Export root check (`exports/policy.py`) | Fixed local drive only | Reject network and removable volumes (`statfs` flags). Returns `True` today: must fail closed instead. |
| Notifications (`notifications/`) | WPF card and shell toast | Off on non-Windows today (`client.py`). Native macOS notification, designed separately. |
| Service channel and launch | Named pipe, `CREATE_NO_WINDOW` | Already portable (`AF_UNIX`, `start_new_session`): verify only. |
| Model environment | `Scripts/python.exe` | Already handled (`bin/python`): verify the ONNX wheels on arm64. |
| Setup (`setup/`, `packaging/windows`) | NSIS with a bundled runtime | Signed and notarized `.pkg` or install script, bundled runtime, `claude` detection outside `.exe`. |
| Shell tools | PowerShell and Git Bash | Bash and zsh: check the exit and failure trailers against zsh. |

## Order

1. Cipher (blocks every vault write on macOS).
2. File writes and the export root check (fail closed until done).
3. Install from source on a real Mac, then the boundary checks of `docs/security/`.
4. Notifications.
5. Packaging, signing, notarization.

## Constraints

- Stdlib only in the hook: Security.framework and CommonCrypto through ctypes.
- No home-made crypto: AES and HMAC come from the OS and the stdlib.
- macOS-only code cannot run on the Windows workstation: it needs a Mac (or a
  macOS CI runner) to be tested; portable logic is tested on both.

## Handoff to the Mac contributor

The founder works on Windows without a Mac; this effort continues on a Mac with
Claude Code. `CLAUDE.md` is git-ignored (it describes the founder's machine), so
start from the tracked guides instead:

1. Read [CONTRIBUTING.md](../../CONTRIBUTING.md) (code standard, tests, install
   rules), [docs/product.md](../../docs/product.md),
   [GLOSSARY.md](../../GLOSSARY.md) and
   [docs/security/threat-model.md](../../docs/security/threat-model.md).
   Product rules that bind every change: fail closed (an error in the hook blocks
   the tool or masks its output), a content-free journal, real values reach the
   disk only through `core/cipher.py`, and the hook stays stdlib-only.
2. Work on `feat/macos`; open a pull request towards `fix/model-boundary-leaks`
   (the Windows 0.1.0-preview.5 line) so the founder can rerun the Windows suite
   before merging.
3. First record a baseline: the suite has never run on macOS. Run
   `python3 -m unittest discover -s tests -t .` with Python 3.12 and list the
   failures and skips in this file before changing code.
4. Then follow the order above, test-first. Do not run
   `python -m privacy_guard install` until the cipher and file writes exist; it
   rewrites `~/.claude/settings.json`, and a broken hook blocks every tool of the
   session (`python -m privacy_guard uninstall` removes it).
5. Synthetic data only, never real files or transcripts.

## Baseline on macOS

Not recorded yet.
