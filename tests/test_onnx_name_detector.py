"""Text preparation and decoding of the ONNX name detector.

These parts are plain Python and run everywhere. The model itself is validated
against GLiNER2 by tools/validate_name_model.py, in the build environment.
"""

import importlib.util
import unittest

from privacy_guard.service.onnx_name_detector import (
    DEFAULT_MODEL_DIR,
    WINDOW_OVERLAP,
    WINDOW_WORDS,
    OnnxNameDetector,
    _best_without_overlap,
    _Candidate,
    _split_words,
    _windows,
)


class SplitWordsTest(unittest.TestCase):
    def test_lowercases_words_and_keeps_original_offsets(self):
        words = _split_words("Léa et Hugo.")

        self.assertEqual([(w.text, w.start, w.end) for w in words],
                         [("léa", 0, 3), ("et", 4, 6), ("hugo", 7, 11), (".", 11, 12)])

    def test_adds_the_final_period_the_model_expects(self):
        self.assertEqual(_split_words("Bonjour Sophie")[-1].text, ".")
        self.assertEqual(_split_words("Bonjour Sophie !")[-1].text, "!")


class WindowsTest(unittest.TestCase):
    def test_short_text_is_a_single_window(self):
        words = list(range(50))

        self.assertEqual(list(_windows(words)), [words])

    def test_long_text_windows_overlap_and_cover_every_word(self):
        words = list(range(1000))

        windows = list(_windows(words))

        self.assertTrue(all(len(window) <= WINDOW_WORDS for window in windows))
        self.assertEqual(windows[1][0], WINDOW_WORDS - WINDOW_OVERLAP)
        self.assertEqual(sorted({word for window in windows for word in window}), words)


class DecodingTest(unittest.TestCase):
    def test_keeps_the_most_confident_of_overlapping_spans(self):
        kept = _best_without_overlap([_Candidate(0, 11, 0.7), _Candidate(0, 4, 0.9), _Candidate(20, 25, 0.6)])

        self.assertEqual(kept, [_Candidate(0, 4, 0.9), _Candidate(20, 25, 0.6)])


@unittest.skipUnless(
    importlib.util.find_spec("onnxruntime") and (DEFAULT_MODEL_DIR / "model.onnx").exists(),
    "needs the model environment and the built model (tools/build_name_model.py)",
)
class ModelTest(unittest.TestCase):
    def test_finds_names_in_prose(self):
        text = "J'ai appelé Jean hier soir, il m'a dit que Sophie Lefèvre passerait demain."

        names = [text[f.start:f.end] for f in OnnxNameDetector().find_names(text)]

        self.assertEqual(names, ["Jean", "Sophie Lefèvre"])


if __name__ == "__main__":
    unittest.main()
