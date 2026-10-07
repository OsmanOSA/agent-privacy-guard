# 01 — Tool names taken for person names

Status: done
Priority: P0 usability
Blocked by: none

## Evidence

In the maintainer's live session (2026-10-07), `Read`, `Bash`, `Grep`, `Write`, `read`,
`write`, `code` and `bash` became `⟦PERSON_NAME:…⟧` in every later tool output,
including source code, plain `echo` output and commit messages. Once a value is
learned in a session it is replaced everywhere, so one false positive spreads.

Effect: the agent can no longer read code that mentions those words, and editing it
risks writing tokens back. A tester would give up.

## Acceptance

- Add the trap to `benchmark/corpus/` first (developer vocabulary in documents and in
  code output), with `⟪…⟫` markup only on real names.
- Find where the propagation happens (session-bound values) and why these words were
  accepted as names in the first place.
- Developer and tool vocabulary is never learned as a name; propagation into
  non-document output requires a stronger signal than a single detection.
- Benchmark: name recall unchanged, no new false alarm.

## Comments

2026-10-07, fixed:

- Cause: `PrivacyCore` reloads every name of the session (`known_names`) and
  `name_spans.propagate` matches them case-insensitively in every later output. One
  legitimate detection ("Madame Read") or a model mistake on the Claude Code
  documentation (288 "names", nearly all "Claude" and "Claude Code") is enough.
- Trap added first: `benchmark/corpus/claude_session_notes.md`. Before the fix:
  5 false alarms, name precision 88%.
- Fix: `core/tool_vocabulary.py`. A name made only of agent, model and tool words is
  dropped at detection and ignored among a session's known names (older vaults).
  "Claude Moreau" is kept. Known limit: a person called only "Claude".
- After: model mode names 97% recall (unchanged), 100% precision, 0 false alarm;
  heuristic mode identical before and after (51% / 100%).
- Rejected: skipping lowercase single-word propagation. Existing tests require a known
  first name to follow into lowercase data (`users = ['alice']`), a real recall need.
  The general risk stays open: a real name that is also a common code word ("Rose")
  would still propagate into code once learned.

Also observed: a `�` inside a word can make the model extend a name over the next
word (over-masking, safe side). Track here if it shows up in the corpus.
