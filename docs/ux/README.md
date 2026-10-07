# Design artifacts and check notes

## UX simulation

Open [privacy-guard.prototype.html](privacy-guard.prototype.html) directly in a modern browser. It contains synthetic hard-coded fixtures and in-memory scenario state; it does not call the runtime, inspect files or contact an agent. Its displayed success states are hypothetical future capability states.

Checked with headless Microsoft Edge on 2026-10-05: initial action gating, illustrative token output, local restoration preview, remote denial, explicit synthetic degraded-mode choice, journal contents, reset, keyboard tabs and containment at 1440px and 390px. No JavaScript page errors were observed. Desktop and narrow-screen captures were inspected visually for readability and layout.

## Archify architecture

### Current implementation (2026-10-07)

[privacy-current.html](privacy-current.html) shows the native Windows implementation at `f278402`, with 22 source references across eight blocks. Download the HTML and open it locally to use the source links, themes and exports. GitHub displays the [PNG export](../assets/privacy-architecture.png) directly in the repository README.

The [specification](privacy-current.architecture.json) and HTML are exact copies of the finalized local artifacts. The earlier editorial changes affect documentation only; none of the cited runtime files differs from the pinned commit. The diagram covers tool-result inspection and the local restoration, vault, name-service and optional notification branches. It does not certify interception of actual model requests.

Archify 3.0.1: all nine showcase checks passed with zero errors or warnings. Delivery, strict artifact checks and the built-in browser gate passed with headless Microsoft Edge. Automated checks covered light mode at 1440×900, 1600×1000, 1920×1080 and 2048×1320, and dark mode at both endpoints. The light 2048px capture, dark 1440px capture and canonical PNG export were inspected for readable blocks, labels and unobstructed arrows. The PNG contains the full diagram without viewer controls. See the [portable validation receipt](privacy-current.validation.json).

To regenerate from the repository root:

```text
node <archify-skill>/bin/archify.mjs finalize architecture docs/ux/privacy-current.architecture.json .archify/architecture-privacy-current-20261007-131021/privacy-current.html --repo-root . --quality showcase --json
```

Set `ARCHIFY_CHROME` to an installed Chromium-based browser if automatic discovery fails. After validation, use **Export → PNG** in the HTML for the README image. Keep the generated HTML and specification together, and update the validation receipt when either changes.

### Earlier target contract (2026-10-05)

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
