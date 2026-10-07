import unittest

from privacy_guard.core.detector import SensitiveDataDetector
from privacy_guard.core.findings import Finding
from privacy_guard.core.name_spans import propagate
from privacy_guard.core.tool_vocabulary import is_tool_vocabulary


class SpanNames:
    """Reports the given words as person names, like an over-eager model."""

    def __init__(self, *words):
        self._words = words

    def find_names(self, text):
        return [Finding("person_name", text.index(word), text.index(word) + len(word))
                for word in self._words if word in text]


def names(text, findings):
    return [text[f.start:f.end] for f in findings if f.kind == "person_name"]


class ToolVocabularyTest(unittest.TestCase):
    def test_names_made_only_of_tool_words(self):
        for name in ("Claude", "Claude Code", "CLAUDE CODE", "Read", "PowerShell", "Grep-Bash"):
            with self.subTest(name=name):
                self.assertTrue(is_tool_vocabulary(name))

    def test_people_and_other_words_are_kept(self):
        for name in ("Claude Moreau", "Moreau", "Sophie Martin", "Codet", ""):
            with self.subTest(name=name):
                self.assertFalse(is_tool_vocabulary(name))


class DetectorVocabularyTest(unittest.TestCase):
    def test_model_findings_made_of_tool_words_are_dropped(self):
        text = "Claude Code relit le plan avec Claude Moreau."
        detector = SensitiveDataDetector(SpanNames("Claude Code", "Claude Moreau"))
        self.assertEqual(names(text, detector.find(text)), ["Claude Moreau"])

    def test_tool_words_remembered_by_an_older_session_are_not_propagated(self):
        text = "Use Read then Bash; Sophie Martin approved."
        found = SensitiveDataDetector(SpanNames()).find_many([text], {"Read", "Bash", "Sophie Martin"})[0]
        self.assertEqual(names(text, found), ["Sophie Martin"])


class SessionPropagationTest(unittest.TestCase):
    def test_code_is_untouched_when_a_tool_word_was_once_reported(self):
        text = "code = read(path)\nclaude --version"
        detector = SensitiveDataDetector(SpanNames())
        self.assertEqual(detector.find_many([text], {"Read", "Code", "Claude"})[0], [])

    def test_lowercase_spellings_of_real_names_still_follow(self):
        text = "users = ['sophie martin', 'alice']"
        found = propagate(text, [], {"Sophie Martin", "Alice"})
        self.assertEqual(names(text, found), ["sophie martin", "alice"])


if __name__ == "__main__":
    unittest.main()
