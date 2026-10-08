# 13 — Rewriting code and configuration files damages them

Status: done
Priority: P1
Blocked by: none

## Evidence

Restoration after Write covered `.txt`, `.md`, `.markdown` and `.csv` only. Measured
with the boundary harness on the `0.1.0-preview.3` executable (Claude Code 2.1.292):

- `write-python`: the agent reads `contacts.py` (a name and an e-mail) and rewrites it
  with the tokens it received. The file kept the tokens: the user's data was replaced
  on disk.
- `write-redacted-secret`: the agent rewrites `.env` with the redaction marker it
  received. The real GitHub token was overwritten for good; a redacted secret is
  never kept, so nothing can restore it. This held for every file type, documents
  included.
- An Edit whose new_string carries a token inserted that token unrestored in code files.

No value reached the model in either case: these are local data-integrity failures.

## Acceptance

- Source code and configuration files get their values back after Write, like documents.
- Edits carrying placeholders in those files take the Write route.
- No tool writes a redaction marker into a file.
- Boundary: both scenarios fail on preview.3 and pass with the fix.

## Comments

2026-10-07, fixed:

- `core/restorable_files.py` is the single list of restorable files (documents, source
  code, configuration, `.env*`), shared by Write restoration, the Edit policy and the
  read guidance. Values go back as they were read, without escaping for the host
  language.
- `claude_code/redacted_writes.py` refuses Write, Edit, MultiEdit and NotebookEdit whose
  new content holds a redaction marker, for any file type, before the tool runs.
- The Edit policy also covers MultiEdit steps.
- Boundary, `--source`: write-python restores `name-3` and `email-2` on disk with
  tokens only in model context; write-redacted-secret is refused and `.env` keeps its
  secret. Both FAIL on the preview.3 executable, as expected. grep-content, secret-env
  and write-restore-reread still pass.
- Spreadsheets other than CSV and binary formats stay out (V2 with their reading).
