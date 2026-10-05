"""Person-name detection with the ONNX model built by tools/build_name_model.py.

Runs without PyTorch (numpy, onnxruntime and tokenizers only): ~1 s to load
instead of ~10 s, ~0.4 GB of memory instead of ~1.8 GB. Text preparation and
span decoding reproduce GLiNER2's own code for the single question "person",
and are validated against it (tests/model/).

Interface: `OnnxNameDetector(model_dir).find_names(text) -> list[Finding]`.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterator

from privacy_guard.core.findings import Finding
from privacy_guard.core.name_detector import PERSON_NAME
from privacy_guard.service.model_files import DEFAULT_MODEL_DIR

MAX_THREADS = 8  # measured: little gain beyond 8 CPU threads
# Attention cost grows with the square of the length: long documents are read
# in overlapping windows of words, so a name cut by one window is whole in the next.
WINDOW_WORDS = 200
WINDOW_OVERLAP = 40

# GLiNER2's whitespace word splitter (gliner2/processing/word_splitter.py), verbatim.
_WORD_PATTERN = re.compile(
    r"""(?:https?://[^\s]+|www\.[^\s]+)
    |[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}
    |@[a-z0-9_]+
    |\w+(?:[-_]\w+)*
    |\S""",
    re.VERBOSE | re.IGNORECASE,
)


@dataclass(frozen=True)
class _Word:
    text: str  # lower-cased, as GLiNER2 feeds it to the model
    start: int
    end: int


@dataclass(frozen=True)
class _Candidate:
    start: int
    end: int
    confidence: float


class OnnxNameDetector:
    """Finds person names anywhere in a text, with or without a label or a title."""

    def __init__(self, model_dir: Path = DEFAULT_MODEL_DIR) -> None:
        import onnxruntime
        from tokenizers import Tokenizer

        config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
        self._prefix_ids: list[int] = config["prefix_ids"]
        self._max_width: int = config["max_width"]
        self._threshold: float = config["threshold"]

        tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        # Words repeat a lot in a document: tokenizing each distinct word once is enough.
        self._word_ids = lru_cache(maxsize=50_000)(
            lambda word: tuple(tokenizer.encode(word, add_special_tokens=False).ids)
        )

        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = min(MAX_THREADS, os.cpu_count() or 1)
        self._session = onnxruntime.InferenceSession(
            str(model_dir / "model.onnx"), options, providers=["CPUExecutionProvider"]
        )

    def find_names(self, text: str) -> list[Finding]:
        words = _split_words(text)
        candidates = [candidate for window in _windows(words) for candidate in self._score(window, text)]
        kept = _best_without_overlap(candidates)
        return sorted((Finding(PERSON_NAME, c.start, c.end) for c in kept), key=lambda f: f.start)

    def _score(self, words: list[_Word],
               text: str) -> Iterator[_Candidate]:
        """Runs the model on one window and yields the spans above the threshold."""
        import numpy

        input_ids, word_positions = self._model_input(words)
        count_logits, span_scores = self._session.run(
            None, {"input_ids": numpy.array([input_ids], dtype=numpy.int64),
                   "word_positions": numpy.array(word_positions, dtype=numpy.int64)},
        )
        if count_logits.argmax() <= 0:
            return  # the model predicts no person in this window

        for start, width in zip(*numpy.nonzero(span_scores >= self._threshold)):
            end = start + width + 1
            if end > len(words):
                continue
            char_start, char_end = words[start].start, min(words[end - 1].end, len(text))
            if text[char_start:char_end].strip():
                yield _Candidate(char_start, char_end, float(span_scores[start, width]))

    def _model_input(self, words: list[_Word]) -> tuple[list[int], list[int]]:
        """The constant question prefix, then each word's subwords; and where each word starts."""
        input_ids = list(self._prefix_ids)
        word_positions = []
        for word in words:
            # A word with no subword keeps a position at the current boundary, as in GLiNER2.
            word_positions.append(len(input_ids))
            input_ids.extend(self._word_ids(word.text))
        return input_ids, word_positions


def _split_words(text: str) -> list[_Word]:
    # GLiNER2 adds a final period when the text does not end with one: the model
    # was trained that way. Offsets past the real text are clipped when decoding.
    if not text.endswith((".", "!", "?")):
        text += "."
    return [_Word(m.group().lower(), m.start(), m.end()) for m in _WORD_PATTERN.finditer(text)]


def _windows(words: list[_Word]) -> Iterator[list[_Word]]:
    step = WINDOW_WORDS - WINDOW_OVERLAP
    for start in range(0, max(len(words) - WINDOW_OVERLAP, 1), step):
        yield words[start:start + WINDOW_WORDS]


def _best_without_overlap(candidates: list[_Candidate]) -> list[_Candidate]:
    """GLiNER2's default decoding: most confident first, skip anything overlapping a kept span."""
    kept: list[_Candidate] = []
    for candidate in sorted(candidates, key=lambda c: c.confidence, reverse=True):
        if not any(candidate.start < other.end and other.start < candidate.end for other in kept):
            kept.append(candidate)
    return kept
