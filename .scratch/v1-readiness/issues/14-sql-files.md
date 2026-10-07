# 14 — SQL files

Status: done
Priority: P1
Blocked by: none

Founder's request (2026-10-07, after the preview.4 freeze): support SQL like CSV.

## Evidence

- Benchmark trap (`seed.sql`, free-text notes column): two person names missed, names
  95% recall. `.sql` reads used quick detection only.
- Boundary `write-sql` on the preview.4 executable: the free-text name of a SQL note
  reached the model.
- Write restoration copied values verbatim: an apostrophe (O'Brien) inside a SQL string
  literal broke the statement or changed its meaning.

## Comments

2026-10-07, fixed:

- `.sql` reads go through the name model (`document_scope.py`). Benchmark: names 100%
  recall, 100% precision, 0 false alarm.
- `exports/sql_content.py` restores values only inside single-quoted literals (quotes
  doubled) and comments; identifiers and bare SQL code keep tokens; an unterminated
  region rejects the restoration. `exports/file_content.py` dispatches by format for
  Write restoration and the export command, which now accepts `.sql` files.
- Boundary `write-sql`: FAIL on preview.4 (name leaked), pass with `--source`: tokens
  only, name and e-mail restored on disk.
