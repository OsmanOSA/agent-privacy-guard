"""Repair only a verified Unicode composition omitted from tokenizer offsets."""

import unicodedata


def complete_compositions(text, windows, normalizer, missing):
    for index in sorted(missing):
        if not unicodedata.combining(text[index]) or index == 0:
            raise ValueError("Tokenizer windows did not cover the complete input")
        base = index - 1
        while base > 0 and unicodedata.combining(text[base]):
            base -= 1
        segment = text[base:index + 1]
        normalized = normalizer.normalize_str(segment) if normalizer else segment
        if normalized != unicodedata.normalize("NFKC", segment) or len(normalized) >= len(segment):
            raise ValueError("Uncovered character is not a verified Unicode composition")
        anchors = [row for window in windows for row in window
                   if row["start"] <= base < row["end"] and row["end"] == index]
        if not anchors:
            raise ValueError("Composed character has no adjacent source token anchor")
        for row in anchors:
            row["end"] = index + 1
