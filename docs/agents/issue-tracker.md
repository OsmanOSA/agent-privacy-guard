# Issue tracker: local Markdown

The founder requested local groundwork before creating a public GitHub repository. Work items therefore live in `.scratch/<effort>/issues/NN-slug.md`, one file per item; the effort's scope lives in `.scratch/<effort>/spec.md`.

Each item has `Status:`, `Priority:` and `Blocked by:` lines. Initial statuses are `open`, `in-progress`, `blocked` and `done`; do not label a security design task as ready for automatic implementation when an unresolved policy is required. Append discussions under `## Comments`.

When a skill says publish to the issue tracker, write a local file. No GitHub, Linear or other remote operation is implied. On migration, preserve the stable local ID, copy sanitized content and link the original decision evidence. Private vulnerability details stay out of this tracker.
