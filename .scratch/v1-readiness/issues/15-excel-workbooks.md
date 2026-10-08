# 15 — Excel workbooks

Status: done
Priority: P1
Blocked by: none

Founder's request (2026-10-07, after the preview.4 freeze): support Excel like CSV.

## Evidence (Claude Code 2.1.292, preview.4 executable)

- `read-xlsx`: Claude Code's Read refuses binary files ("use a shell command or script
  that can read the format"); nothing reaches the model.
- `shell-xlsx`: `python read_xlsx.py clients.xlsx` prints the cells; a free-text name of a
  note column reached the model (workbook commands used quick detection only).
- `write-xlsx`: a script saving the received tokens in `report.xlsx` left tokens in the
  cells: the user's workbook held placeholders.

## Comments

2026-10-07, fixed:

- Commands naming `.xlsx`, `.xlsm`, `.xls` or `.ods` go through the name model
  (`document_scope.py`).
- `exports/excel_content.py` restores text cells only (shared strings, inline strings),
  XML-escaped; formulas, numbers and other parts are copied unchanged; non-workbooks and
  archives over 64 MiB decompressed are rejected.
- `exports/written_workbook.py` applies it in place with the native guarantees of Write
  restoration; `claude_code/workbook_restoration.py` runs it after a successful
  foreground shell command, for each existing `.xlsx`/`.xlsm` the command names.
- Boundary with `--source`: shell-xlsx and write-xlsx pass (5 values restored in the
  workbook, tokens only in model context); both FAIL on preview.4. Benchmark unchanged:
  100% recall and precision.
- Left for V1.1: workbooks written by inline code that does not name them; `.xls` and
  `.ods` restoration.
