import unittest

from privacy_guard.service.cached_names import CachedNameDetector
from tests.fakes import RecordingNameService


class NameCacheTest(unittest.TestCase):
    def setUp(self):
        self.detector = RecordingNameService()
        self.cache = CachedNameDetector(self.detector)

    def test_reuses_exact_text_and_returns_independent_lists(self):
        text = "Nom : Jean Dupont"
        first = self.cache.find_names(text)
        expected = list(first)
        first.clear()
        self.assertEqual(self.cache.find_names(text), expected)
        self.assertEqual(self.detector.queried, [text])

    def test_changed_text_and_whitespace_are_analyzed_again(self):
        for text in ["Nom : Jean Dupont", "Nom : Marie Martin", "Nom : Jean Dupont\n"]:
            self.cache.find_names(text)
        self.assertEqual(len(self.detector.queried), 3)

    def test_empty_success_is_cached(self):
        self.assertEqual(self.cache.find_names("No names here"), [])
        self.assertEqual(self.cache.find_names("No names here"), [])
        self.assertEqual(len(self.detector.queried), 1)

    def test_new_detector_configuration_starts_empty(self):
        self.cache.find_names("Nom : Jean Dupont")
        other = CachedNameDetector(self.detector)
        other.find_names("Nom : Jean Dupont")
        self.assertEqual(len(self.detector.queried), 2)

    def test_failure_is_not_cached_and_can_recover(self):
        class Unavailable:
            calls = 0

            def find_names(self, text):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("Detector unavailable")
                return []

        detector = Unavailable()
        cache = CachedNameDetector(detector)
        with self.assertRaises(RuntimeError):
            cache.find_names("A document")
        self.assertEqual(cache.find_names("A document"), [])
        self.assertEqual(cache.find_names("A document"), [])
        self.assertEqual(detector.calls, 2)

    def test_entry_limit_evicts_least_recently_used(self):
        cache = CachedNameDetector(self.detector, max_entries=2)
        for text in ["A", "B", "A", "C", "B"]:
            cache.find_names(text)
        self.assertEqual(self.detector.queried, ["A", "B", "C", "B"])

    def test_total_finding_limit_evicts_old_results(self):
        cache = CachedNameDetector(self.detector, max_findings=1)
        for text in ["Nom : Jean Dupont", "Nom : Marie Martin", "Nom : Jean Dupont"]:
            cache.find_names(text)
        self.assertEqual(len(self.detector.queried), 3)

    def test_oversized_result_is_returned_but_not_cached(self):
        cache = CachedNameDetector(self.detector, max_findings=1)
        text = "Nom : Jean Dupont\nNom : Marie Martin"
        self.assertEqual(len(cache.find_names(text)), 2)
        self.assertEqual(len(cache.find_names(text)), 2)
        self.assertEqual(len(self.detector.queried), 2)

    def test_invalid_limits_are_rejected(self):
        for options in [{"max_entries": 0}, {"max_findings": 0}]:
            with self.assertRaises(ValueError):
                CachedNameDetector(self.detector, **options)


if __name__ == "__main__":
    unittest.main()
