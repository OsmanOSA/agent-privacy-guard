"""Unicode rules between tool output and the tokenizer.

Interface:
    tokenizable(text) -> str          same-length text the tokenizer accepts
    must_be_covered(char) -> bool     characters the model must have seen
    complete_compositions(...)        repair a verified composition missing from offsets

Windows command output often carries undecodable bytes (lone surrogates) and
replacement or control characters. The tokenizer rejects the former and skips the
latter; either used to fail the whole inspection, which masked the complete output.
Coverage is still required for every character that can belong to a name.
"""

import unicodedata


def tokenizable(text: str) -> str:
    """Replace lone surrogates with spaces, keeping every offset unchanged."""
    return "".join(" " if unicodedata.category(char) == "Cs" else char for char in text)


def must_be_covered(char: str) -> bool:
    """Letters, marks and digits: a skipped one could hide part of a name."""
    return unicodedata.category(char)[0] in "LMN"


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
