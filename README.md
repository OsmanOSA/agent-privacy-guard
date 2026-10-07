# Agent Privacy Guard

A local privacy layer for AI coding agents. It replaces detected sensitive values in tool results with session-scoped tokens and restores approved personal values in local files written through its supported workflow.

**Claude Code first; other agents later.** The current implementation targets Claude Code on native Windows, using Windows DPAPI for the vault. macOS, Linux, Codex and other adapters are future work, each subject to its own compatibility and security evidence.

**Status: research prototype, not a verified security boundary.** Registering a hook is not proof that every path to a model is protected. See the [security baseline](docs/security/baseline-2026-10-05.md) for observed gaps and the [threat model](docs/security/threat-model.md) for the intended guarantee.

## Start here

| You want to… | Read |
| --- | --- |
| Assess what exists and what to validate next | [Project assessment](docs/project-assessment.md) |
| Understand the product and its scope | [Product brief](docs/product.md) |
| Understand the modules and data flow | [Architecture](docs/architecture.md) |
| Explore the proposed experience | [UX flows](docs/ux/flows.md) and [interactive mockup](docs/ux/privacy-guard.prototype.html) |
| Contribute a rule, test, doc or adapter | [Contributing](CONTRIBUTING.md) |
| Pick a bounded task | [Roadmap](docs/roadmap.md) |
| Understand decisions and terminology | [Context](CONTEXT.md), [glossary](GLOSSARY.md), [ADRs](docs/adr/) |
| Prepare the first public repository | [Publication and release guide](docs/releasing.md) |
| Report a vulnerability | [Security policy](SECURITY.md) |

## Try the development checks

From the project root, with Python 3.12 (the baseline environment):

```powershell
python -m unittest discover -s tests -t .
python -m benchmark --spaced
```

These checks use synthetic fixtures and temporary directories. They do not prove what a real Claude Code process sends to its model. The default benchmark falls back to heuristic name detection when the model dependencies are unavailable; always report that mode with scores.

Use only synthetic data while evaluating this prototype. Installation changes local Claude Code settings, copies the engine outside this folder and may download model dependencies. Read [Contributing](CONTRIBUTING.md#installation-is-a-separate-action) before installing.

Compatible updates keep the session vaults and their tokens. If an existing vault format is unknown or incompatible, installation stops without deleting it. Uninstall still removes session vaults.

Python reads use rules and contextual name heuristics, without a NER call. Document reads use the selected French DistilCamemBERT ONNX FP32 detector when installed. The background process reuses exact-text detections in a bounded memory cache, while every read still applies the current session's pseudonymization. See the [integration and measured limits](docs/architecture.md#distilcamembert-integration).

New personal mappings are stored as DPAPI-encrypted payloads in a per-session SQLite database, grouping vault access without changing token identifiers. Legacy encrypted files remain readable. On this machine, three installed-hook runs measured a median of 1.68 s for an unseen 3,997-token document and 295 ms for its identical reread, with the model already loaded. See the [storage changes and timing conditions](docs/architecture.md#transactional-encrypted-vault-storage).

Protection changes now emit native Claude Code user messages with category occurrence counts and the document basename. The same metadata is recorded locally in `~/.privacy-guard/logs/protection.jsonl`, without extracted body values, full paths or token identifiers. Local restoration emits a native status message. Handled post-tool inspection errors request an immediate stop; sensitive failed-tool errors also stop. Hook absence/timeouts and retained original error history remain limitations. See [failure handling and native notices](docs/architecture.md#handled-failures-and-native-user-notices).

The 2026-10-07 correction completes detected name words and protects other occurrences of their complete spellings, including case variants, across tool results within one session. It reuses existing encrypted person mappings without a separate plaintext index and corrects demonstrated token-metric and diff-decorator false positives. Handled errors now record fixed processing stages and error categories in `~/.privacy-guard/logs/failures.jsonl`, without source values or exception messages. This revision and the INSEE index were deployed to the user's global installation on explicit request, preserving existing vault files and settings. Inferring name aliases, image/OCR extraction and historical-token handling remain separate limitations. See the [initial session feedback review](docs/architecture.md#session-feedback-review-2026-10-07), [session recognition and diagnostics](docs/architecture.md#session-wide-recognition-and-failure-diagnostics-2026-10-07) and [global upgrade evidence](docs/architecture.md#global-upgrade-2026-10-07).

An optional INSEE lexicon now complements rules and NER in explicit personal fields, including lowercase first names and isolated surnames. It never rejects a NER finding because a name is absent from INSEE, and does not blanket-mask dictionary words or paths. Prepare the pinned public files locally with `python tools/prepare_insee_lexicon.py --output evaluation/ner/data/insee/data/insee-names.sqlite`. This destination is ignored by Git and is not the global installation. Runtime discovers an explicitly prepared index at `<guard-home>/data/insee-names.sqlite`; that index is now installed on this machine. Deployment on another machine remains an explicit action. See the [integration and limits](docs/architecture.md#optional-insee-name-lexicon-2026-10-07) and [data attribution](licenses/INSEE-data-NOTICE.txt).

## Optional Windows desktop notifications

Desktop notifications default to off on a new installation. A detached local worker groups successful protection summaries by session and checks the originating window at delivery. The selected presentation is a dark, rounded Privacy Guard card inspired by Driftlight. A native Windows banner is the fallback. The card prepares invisibly and checks foreground and quiet state again before display; Windows owns native banner delivery.

After explicitly deploying the updated hook, enable background-only delivery:

```powershell
python -m privacy_guard notifications --notification-mode background --notification-style card
python -m privacy_guard notifications
```

Use `--notification-mode always` to receive grouped notices even in the foreground, or `--notification-mode off` to stop them and clear pending summaries. `--notification-style native` selects the Windows banner without a custom card. `--notification-test` shows one synthetic notice using the selected style, independently of hook installation. Choosing a style alone leaves the enable/disable preference unchanged. Status reports mode, style and whether notification hook code is deployed.

Notices contain category occurrence counts and bounded document metadata, never extracted values or body text. Basenames can themselves be identifying. A known foreground window suppresses the desktop notice; an ambiguous host uses grouped delivery. This does not identify a particular VS Code chat tab or every Windows Terminal pane. The card uses the verified host's monitor, or the foreground monitor when its origin is unknown. Its return button revalidates the host process before requesting focus; Windows can refuse that request.

The custom card closes after ten seconds unless hovered, with a sixty-second maximum lifetime. It opens without taking focus and closes if foreground or quiet-state changes require suppression. Quiet detection combines the Windows presentation/fullscreen API and a read-only, undocumented quiet-profile adapter. An unknown state uses the native banner instead of a custom popup. This is a compatibility fallback, not a guaranteed public API for every Windows Do Not Disturb configuration. Both notification modes respect detected quiet state, including `always`.

Windows 11 native banners are transient. The custom card has no Windows notification-center history. Native Claude Code messages remain active regardless of desktop preference. See the [implementation and evidence](docs/architecture.md#optional-windows-desktop-notifications-2026-10-07).

## Community and licensing

Agent Privacy Guard is licensed under the [MIT License](LICENSE), copyright 2026 OsmanOSA. Keep the copyright and license notice with copies of the code.

A private vulnerability-reporting channel still needs to be established before opening external contributions; see [governance](GOVERNANCE.md).

The earlier French [PRD](PRD.md) is retained as a vision document. The [product brief](docs/product.md) defines the current delivery scope. Technical conventions live in [Contributing](CONTRIBUTING.md).
