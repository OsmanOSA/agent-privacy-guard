# Groundwork tooling provenance

Skills installed outside the project on 2026-10-05 using the bundled skill-installer helper. Versions are pinned for provenance; no third-party skill runtime is a dependency of Privacy Guard.

| Source | Revision | Installed skills |
| --- | --- | --- |
| [Matt Pocock skills](https://github.com/mattpocock/skills) | `4588b32ecab9ecc9fc8cc6b6c5e7d675b6004b0d` | setup-matt-pocock-skills, domain-modeling, codebase-design, to-spec, prototype |
| [Archify](https://github.com/tt-a1i/archify) | `73aaa0696e8f72c232ea710e6fa94fd953f3e773` | archify |

Applied disciplines: local issue tracker and single-context domain documents; a glossary with precise privacy terms; concise architecture decisions; small interfaces and existing test seams. The scope and local destination came directly from the founder's request; no remote tracker was configured.

The Archify diagram is a **target design**, not a verified diagram of a committed repository. This workspace had no Git identity at inspection, so no revision or remote was invented. The current source mapping is documented separately in `docs/architecture.md`.

The UX mockup is an in-memory design artifact. It does not inspect documents, control hooks, send telemetry or represent an implemented application. No skill code is copied into the project runtime.
