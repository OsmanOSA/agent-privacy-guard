# Agent Privacy Guard

Local layer that pseudonymizes the sensitive data AI coding agents discover on the machine. Product, scope and promise: [PRD.md](PRD.md) (in French).

## Code standard

Open source project: everything in the repo is in English (code, comments, docstrings, user-facing messages, docs). Senior-level, readable, polished code.

- **One function = one task.** A class groups methods that each do one thing.
- **Short modules**: aim under 200 lines and split as soon as a module carries two responsibilities. 1000 lines is a hard limit, never reached.
- **Deep modules** (vocabulary from the `codebase-design` skill): small interface, logic hidden behind it. Dependencies are injected (e.g. the journal passed to the hook) so behaviour is tested through the interface.
- **Comments explain the why**: constraint, risk, non-obvious choice. Every module opens with a docstring giving its role and interface.
- Python standard library only: the hook starts on every tool call and must run without installing dependencies.

## Product rules the code must honour

- **Fail closed**: any error in the hook blocks the tool (PreToolUse) or masks its output (PostToolUse). Nothing unchecked reaches the model.
- **Content-free journal**: record the kind of event ("email pseudonymized"), never the value.
- **Encrypted vault, OS-native only**: real values reach the disk only through `core/cipher.py` (Windows DPAPI today, macOS Keychain + CommonCrypto next). No home-made crypto; no install where no OS cipher exists.
- **V1 scope: Claude Code only.** Other agents come once Claude Code is validated.
- **The user's prompt is out of scope** (PRD §15): protect only what the agent reads on its own (files, command output, MCP results).

## Working on the hook

- Tests: `python -m unittest discover -s tests -t .` from the repo root. They use temp directories, never the real `~/.claude`.
- Quality: any change to what is detected is measured with `~/.privacy-guard/model-env/Scripts/python -m benchmark --spaced` (annotated corpus in `benchmark/corpus/`, markup `⟪category:value⟫`). Recall and precision must not drop; a new kind of document or trap goes into the corpus first. `--spaced` keeps values readable through the protection itself.
- The hook is installed on this machine and runs on every tool of the current session. A code change takes effect only after `python -m privacy_guard install`, which redeploys to `~/.privacy-guard/app`.
- Get the tests green before every redeploy: a broken hook blocks every tool of the session, including the ones needed to fix it. Emergency removal from a terminal: `python -m privacy_guard uninstall`.

## Name model (background service)

- Person names in documents come from GLiNER2-PII, converted to a 4-bit ONNX graph that runs without PyTorch (`privacy_guard/service/onnx_name_detector.py`). The hook stays stdlib-only; only the service needs `numpy`, `onnxruntime` and `tokenizers`, pinned in `service/model_environment.py` and installed by `python -m privacy_guard install` into `~/.privacy-guard/model-env`.
- The model files are verified by SHA-256 (`service/model_files.py`) before every use. `install --model-source DIR_OR_HTTPS_URL` fetches them.
- The model's raw output goes through `PlausibleNameFilter` (core/name_detector.py), which drops what cannot be a name in developer documents (URL and path fragments, `GLiNER2`, `ONNX`). Validation compares the raw model, before this filter.
- Building the model is separate, in an environment created from `tools/requirements-build.txt`: `tools/build_name_model.py`, then `tools/validate_name_model.py`, which must report every text identical to GLiNER2. A new build means new hashes in `MANIFEST`. `tools/prepare_model_release.py` prepares the files and model card for publication on Hugging Face, outside the project folder.

## Scope and evidence

The fail-closed rules above are required design outcomes, not a proven guarantee of the current runtime. Read `docs/security/baseline-2026-10-05.md` for protocol, restoration and installation gaps before changing or advertising protection. Hook registration, unit tests and detection scores are different from observed model-boundary enforcement. Current delivery scope lives in `docs/product.md`; the French PRD preserves the broader vision.

Use synthetic fixtures only. Do not install/redeploy into the user's live agent, initialize Git, create a remote, push or publish as a side effect of documentation or source tests. Follow `docs/releasing.md` when publication is explicitly requested.

## Agent skills

### Issue tracker

Work items are local Markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`; no remote tracker is configured.

### Domain docs

Single-context glossary and concise ADRs at the project root. See `docs/agents/domain.md`, `GLOSSARY.md` and `docs/adr/`.
