# 12 — Technical file names masked as person names

Status: done
Priority: P1
Blocked by: none

## Evidence

In the live session, `ls` of the issue folder showed `01-tool-name-false-positives.md`
masked: the INSEE index lists "name" as a given name and "false" as a family name.
Measured on 30,300 real file names (Python standard library, site-packages, this
repository): 663 (2.2%) matched, mostly identifier words (`per_channel`, `copy_native`,
`loss_meta`). In a PyTorch project every Glob would mask files and break the paths the
agent works with.

## Acceptance

- Technical words come from a measured vocabulary, not only a hand list.
- No common French given or family name is lost.
- Benchmark: the traps go into `benchmark/corpus/file_listing.out` first; recall and
  precision do not drop.

## Comments

2026-10-07, fixed:

- `tools/build_code_words.py` generates `privacy_guard/core/code_words.py`: identifier
  parts (snake_case and camelCase) found in at least 3 modules of the Python standard
  library, never comments or strings (2,476 words). The file-name detector adds them to
  its hand list.
- 663 → 67 matched file names (0.22%); what remains is mostly proper nouns
  (`barnes_hut`, `hong_kong`) and real names (`thomas_girard` in a fixture).
- 0 of 135 common French names fall in the vocabulary (unit test on a sample).
- Benchmark with 8 new traps and one more real name: names 100% recall, 100% precision.
