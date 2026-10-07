import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from privacy_guard.core.findings import Finding
from privacy_guard.service.__main__ import _load_detector
from privacy_guard.service.distil_name_detector import DistilNameDetector
from privacy_guard.service.model_files import ModelFilesError
from privacy_guard.service.ner_spans import decode
from privacy_guard.service.ner_policy import record_model, requires_model, remove_model


class DistilRuntimeTest(unittest.TestCase):
    def test_person_only_decode_merges_overlapping_windows(self):
        text = "Jean Dupont à Paris"
        rows = [{"label": "I-PER", "start": 0, "end": 4, "score": 0.9},
                {"label": "I-PER", "start": 5, "end": 11, "score": 0.8},
                {"label": "I-LOC", "start": 14, "end": 19, "score": 0.99}]
        self.assertEqual(decode(text, {"encoding": "tokens", "windows": [rows, rows[1:]]}, 0.5),
                         [{"kind": "PERSON", "start": 0, "end": 11}])

    def test_calibrated_threshold_is_preserved(self):
        row = {"label": "I-PER", "start": 0, "end": 4, "score": 0.49}
        self.assertEqual(decode("Jean", {"encoding": "tokens", "windows": [[row]]}, 0.5), [])

    def test_missing_bundle_is_rejected_before_optional_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ModelFilesError):
                DistilNameDetector(Path(directory))

    def test_document_model_failure_is_not_silently_downgraded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("privacy_guard.service.distil_name_detector.DistilNameDetector",
                       side_effect=ModelFilesError("Tampered bundle")):
                with self.assertRaises(ModelFilesError):
                    _load_detector(root / "service.log", root)
            self.assertIn("document detection blocked", (root / "service.log").read_text())

    def test_service_uses_heuristic_plus_distil_without_legacy_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # The calibrated model result is not dropped by the old acronym filter.
            detector = unittest.mock.Mock()
            detector.find_names.return_value = [Finding("person_name", 0, 3)]
            with patch("privacy_guard.service.distil_name_detector.DistilNameDetector", return_value=detector):
                combined = _load_detector(root / "service.log", root)
            self.assertEqual(combined.find_names("LÉA"), detector.find_names.return_value)

    def test_missing_model_uses_the_explicit_optional_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            detector = _load_detector(root / "service.log", root / "absent")
            self.assertEqual(len(detector.find_names("Nom : Jean Dupont")), 1)
            self.assertIn("heuristic only", (root / "service.log").read_text())

    def test_required_model_missing_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ModelFilesError):
                _load_detector(root / "service.log", root / "absent", required=True)

    def test_successful_installation_requirement_survives_missing_weights(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertFalse(requires_model(root))
            record_model(root)
            self.assertTrue(requires_model(root))
            remove_model(root)
            self.assertFalse(requires_model(root))

    def test_corrupt_model_policy_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ner-model.json").write_text("{}")
            with self.assertRaises(ModelFilesError):
                requires_model(root)


if __name__ == "__main__":
    unittest.main()
