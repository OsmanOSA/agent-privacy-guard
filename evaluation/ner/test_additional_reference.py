"""Check alignment against published reference files, without generated corpus text."""

import json
import re
import unittest

from .additional_cohort import RAW, RUN, TASKS
from .europeana import read as read_europeana
from .metrics import Metrics, validate_spans
from .score import evaluate, load_rows
from .sequoia import read as read_sequoia
from .soduco import read as read_soduco
from .unicode_offsets import complete_compositions


class ReferenceAlignmentTests(unittest.TestCase):
    def test_composed_accent_offsets_and_actual_missing_content(self):
        from tokenizers import Tokenizer
        from .fetch import BASE

        row = load_rows(RUN / "europeana-newspapers-fr.jsonl")["europeana-newspapers-fr:58"]
        tokenizer = Tokenizer.from_file(str(BASE / "models/distilcamembert-base-ner/tokenizer.json"))
        encoded = tokenizer.encode(row["text"])
        windows = [[{"start": start, "end": end} for (start, end), special in zip(encoded.offsets, encoded.special_tokens_mask) if not special]]
        complete_compositions(row["text"], windows, tokenizer.normalizer, {268})
        self.assertTrue(any(item["start"] == 267 and item["end"] == 269 for item in windows[0]))
        with self.assertRaisesRegex(ValueError, "complete input"):
            complete_compositions(row["text"], windows, tokenizer.normalizer, {267})

    def test_sequoia_uses_typed_ne_and_excludes_wikipedia(self):
        excluded = []
        rows = list(read_sequoia(RAW / "sequoia-ud.parseme.frsemcor", excluded))
        self.assertEqual(len(rows), 2102)
        self.assertEqual([row["source_id"] for row in excluded], ["annodis.er_00157"])
        self.assertFalse(any("frwiki_50.1000" in row["id"] for row in rows))
        self.assertEqual(sum(len(row["spans"]) for row in rows), 270)
        first = rows[0]
        self.assertEqual(first["text"][first["spans"][0]["start"]:first["spans"][0]["end"]], "Gutenberg")
        self.assertTrue(all("NE-PERS." in span["source_label"] for row in rows for span in row["spans"]))

    def test_xml_text_matches_source_and_nested_spans_are_preserved(self):
        excluded = []
        rows = list(read_soduco(RAW / "soduco.json", excluded))
        self.assertEqual(len(rows), 8762)
        self.assertEqual(len(excluded), 3)
        source = json.loads((RAW / "soduco.json").read_text(encoding="utf-8"))
        by_id = {f"soduco-nested-ner:{r['book']}:{r['page']}:{r['id']}": r for r in source}
        for row in rows:
            self.assertEqual(row["text"], by_id[row["id"]]["text_ocr_ref"])
            validate_spans(row["text"], row["spans"])
            self.assertFalse(any(s["kind"] == "PERSON" for s in row["spans"]))
        first = rows[0]
        address = next(s for s in first["spans"] if s["kind"] == "ADDRESS")
        street = next(s for s in first["spans"] if s["kind"] == "STREET")
        self.assertLessEqual(address["start"], street["start"])
        self.assertGreaterEqual(address["end"], street["end"])

    def test_europeana_chunks_preserve_all_tokens_without_entity_cuts(self):
        rows = list(read_europeana(RAW / "europeana.bio"))
        source = [line.rsplit(None, 1) for line in (RAW / "europeana.bio").read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(sum(row["token_count"] for row in rows), 205916)
        for row in rows:
            start, end = row["source_token_start"], row["source_token_end"]
            self.assertEqual(row["text"], " ".join(token for token, _ in source[start:end]))
            if end != len(source):
                self.assertEqual(source[end - 1][1], "O")
            self.assertEqual(row["source_tag_anomalies"], {})

    def test_reference_scores_one_and_wrong_offsets_are_not_exact(self):
        for dataset, kind in TASKS.items():
            rows = load_rows(RUN / f"{dataset}.jsonl")
            predictions = {key: {"text_sha256": row["text_sha256"],
                "spans": [span for span in row["spans"] if span["kind"] == kind]} for key, row in rows.items()}
            self.assertEqual(evaluate(rows, predictions, "test", kind)["quality"]["exact_f1"], 1.0)
        row = next(row for row in rows.values() if any(s["kind"] == kind and s["end"] - s["start"] > 1 for s in row["spans"]))
        gold = next(s for s in row["spans"] if s["kind"] == kind and s["end"] - s["start"] > 1)
        metric = Metrics()
        metric.add(row["text"], [gold], [{**gold, "start": gold["start"] + 1}])
        self.assertEqual(metric.report()["exact_f1"], 0.0)


if __name__ == "__main__":
    unittest.main()
