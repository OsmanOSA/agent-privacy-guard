"""Describe coverage misses without publishing reference names or text."""

from collections import Counter

from .metrics import character_positions


def coverage_errors(corpus, predictions):
    buckets = {}
    for key, row in corpus.items():
        found = [s for s in predictions[key]["spans"] if s["kind"] == "PERSON"]
        positions = character_positions(row["text"], found)
        for span in row["spans"]:
            if span["kind"] != "PERSON":
                continue
            expected = character_positions(row["text"], [span])
            status = "complete" if expected <= positions else "partial" if expected & positions else "missed_entirely"
            category = span.get("source_label", "PERSON")
            bucket = buckets.setdefault(category, Counter())
            bucket[status] += 1
            bucket["mentions"] += 1
    return {kind: dict(counts) for kind, counts in buckets.items()}
