# Agent Privacy Guard

A local privacy layer for AI coding agents. It replaces detected sensitive values in tool results with session-scoped tokens and restores them for selected local tool calls.

**Claude Code first; other agents later.** The current implementation targets Claude Code on native Windows, using Windows DPAPI for the vault. macOS, Linux, Codex and other adapters are future work, each subject to its own compatibility and security evidence.

**Status: research prototype, not a verified security boundary.** Registering a hook is not proof that every path to a model is protected. See the [security baseline](docs/security/baseline-2026-10-05.md) for observed gaps and the [threat model](docs/security/threat-model.md) for the intended guarantee.

## Start here

| You want to… | Read |
| --- | --- |
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

## Community and licensing

Agent Privacy Guard is licensed under the [MIT License](LICENSE), copyright 2026 OsmanOSA. Keep the copyright and license notice with copies of the code.

A private vulnerability-reporting channel still needs to be established before opening external contributions; see [governance](GOVERNANCE.md).

The earlier French [PRD](PRD.md) is retained as a vision document. The [product brief](docs/product.md) defines the current delivery scope. Technical conventions live in [CLAUDE.md](CLAUDE.md) and [Contributing](CONTRIBUTING.md).
