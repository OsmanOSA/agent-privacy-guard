# Windows setup preview

The setup includes Python, the French DistilCamemBERT ONNX model, the prepared
INSEE name index and Claude Code hooks. End users do not need Python, pip, Git
or a model download. Claude Code must already be installed and opened once.

This research preview retains the [known integration limits](security/baseline-2026-10-05.md).
It targets native Windows x64, with Windows 10 as the minimum. Packaging checks
currently run on the maintainer's Windows 11 machine. ARM64, WSL, macOS and Linux
are outside this package's scope.

## Install

1. Close running Claude Code sessions.
2. Run `PrivacyGuard-0.1.0-preview.4-windows-x64.exe` and follow the wizard. The
   installation directory may be at most 107 characters long; the default is shorter.
3. Start a new Claude Code session in VS Code or a terminal.

The setup registers hooks in the current user's Claude Code configuration,
including `CLAUDE_CONFIG_DIR` when defined. It preserves unrelated settings and
hooks and refuses a configuration with `disableAllHooks` enabled. Managed settings
can override user settings. Registration does not prove complete model-boundary coverage.

The Start menu entry **Verifier Privacy Guard** checks registration and executes
the included detector. Ordinary Claude web/desktop conversations are not covered.
A first install enables background desktop notifications using the dark card;
existing preferences survive upgrades and reinstalls.

## Storage and removal

- Bundled runtime: `%LOCALAPPDATA%\Programs\PrivacyGuard`.
- Engine, model, preferences and encrypted mappings: `%USERPROFILE%\.privacy-guard`.
- Hook settings: `%USERPROFILE%\.claude\settings.json`, unless overridden.

Installation requires no administrator account, changes no PATH and adds no Windows
service. Model and notification processes start on demand. Allow roughly 1.5 GB of
free space for extraction, the installed model and upgrade backups; the requirement
depends on the previous installation.

Builds have separate version directories. An identical setup can register hooks
again; a different payload with the same version is rejected. A damaged runtime
needs a newer setup or removal followed by installation. Activation failures restore
the previous owned files and Claude settings and retain a recovery snapshot.
This does not guarantee recovery from power loss during installation.

Remove Privacy Guard through Windows Installed apps or its Start menu entry.
The Windows uninstaller removes hooks and the current packaged runtime. It retains
the encrypted mappings, deployed engine, model, logs and preferences in
`.privacy-guard`; older version directories also remain. These retained files do
not keep hooks active. The development CLI's uninstall also purges session vaults.

## Release status

Build scripts produce a local `.exe` and SHA-256 file in `dist/`. There is no public
Windows download advertised yet. Builds are not Authenticode signed, so Windows
may show an unknown-publisher/SmartScreen warning.

Before advertising a public download: test a clean Windows account without Python,
check actual Claude Code sessions in VS Code and the terminal, establish code signing,
and complete the applicable [release gates](releasing.md#gate-b--ship-an-installable-alpha).
Isolated automated setup checks do not replace those checks.

OCR and binary extraction are deferred to [issue #1](https://github.com/OsmanOSA/agent-privacy-guard/issues/1).
See [build instructions](../packaging/windows/README.md).

Recorded checks and artifact hashes: [preview.4 receipt](windows-setup-checks-2026-10-07-preview-4.md)
(earlier: [preview.3](windows-setup-checks-2026-10-07-preview-3.md), [preview.2](windows-setup-checks-2026-10-07-preview-2.md),
[preview.1](windows-setup-checks-2026-10-07.md)).
