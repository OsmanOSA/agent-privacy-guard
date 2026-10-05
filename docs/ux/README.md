# Design artifacts and check notes

## UX simulation

Open [privacy-guard.prototype.html](privacy-guard.prototype.html) directly in a modern browser. It contains synthetic hard-coded fixtures and in-memory scenario state; it does not call the runtime, inspect files or contact an agent. Its displayed success states are hypothetical future capability states.

Checked with headless Microsoft Edge on 2026-10-05: initial action gating, illustrative token output, local restoration preview, remote denial, explicit synthetic degraded-mode choice, journal contents, reset, keyboard tabs and containment at 1440px and 390px. No JavaScript page errors were observed. Desktop and narrow-screen captures were inspected visually for readability and layout.

## Archify architecture

Open [privacy-target.html](privacy-target.html). It is a **proposed incoming tool-result disclosure contract**, not a verified architecture diagram of committed source. It does not claim filesystem isolation or comprehensive restoration enforcement.

Authored specification: [privacy-target.architecture.json](privacy-target.architecture.json). The JSON retains the original local generation destination under `.archify/`; the documentation HTML is an exact byte copy of that artifact.

Archify 3.0.1 checks: showcase validation **passed**, artifact delivery **passed**, strict artifact check **passed**. Its built-in browser gate **failed** because the Windows Edge DevTools pipe ended before a response. Therefore the complete Archify `finalize` invocation did **not** pass.

An independent Playwright/Edge run rendered those exact bytes, found no page errors, checked horizontal containment at 1440×900, 1600×1000, 1920×1080 and 2048×1320, and produced a desktop capture that was visually inspected. This check does not substitute for Archify's full theme/Reader-state browser gate. Keep the automated-gate limitation explicit on handoff.

Artifact SHA-256: `c41fcfecb4153ee333cfd56c90f020facfb5739d0b8f2d78e18e44a8f19ef947`.

To reproduce with an installed skill, replace `<archify-skill>` with its actual location:

```text
node <archify-skill>/bin/archify.mjs finalize architecture docs/ux/privacy-target.architecture.json .archify/architecture-privacy-target-20261005-164328/privacy-target.html --quality showcase --json
```

Use a browser-capable environment for the full gate. Local receipts/captures remain excluded by `.gitignore` because they can contain machine-specific paths. Source references for today's implementation are in [architecture](../architecture.md), independently of this target design.

## Third-party material

The generated diagram includes Archify's viewer, licensed under MIT: preserve [ARCHIFY-LICENSE.txt](ARCHIFY-LICENSE.txt). It includes the JetBrains Mono font under SIL OFL 1.1: preserve [JetBrainsMono-OFL.txt](JetBrainsMono-OFL.txt). Keep [upstream third-party notices](ARCHIFY-THIRD-PARTY-NOTICES.md) with a redistributed diagram. These notices apply to the generated viewer assets; the project's MIT license is in [LICENSE](../../LICENSE).
