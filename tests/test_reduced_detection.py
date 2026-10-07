import json
import tempfile
import time
import unittest
from pathlib import Path

from privacy_guard.claude_code.protection import protect_tool_output
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from privacy_guard.notifications.presentation import banner_text, card_content
from privacy_guard.notifications.queue import NotificationQueue
from privacy_guard.protection_summary import ProtectionSummary
from privacy_guard.service.cached_names import CachedNameDetector
from privacy_guard.service.reduced_names import ReducedNameDetector
from tests.fakes import ReversingCipher

READ = {"tool_name": "Read", "tool_input": {"file_path": "C:/docs/notes.md"}}


class ReducedSummaryTest(unittest.TestCase):
    def test_message_warns_even_without_any_detection(self):
        message = ProtectionSummary({}, "C:/docs/notes.md", "model_runtime").message()
        self.assertTrue(message.startswith("Privacy Guard — notes.md : détection des noms réduite"))
        self.assertIn("certains noms peuvent rester visibles", message)

    def test_reason_is_allowlisted_and_recorded(self):
        self.assertEqual(ProtectionSummary({"email": 1}, None, "model_files").record()["reduced"], "model_files")
        with self.assertRaises(ValueError):
            ProtectionSummary({}, None, "bad allocation at 0x1")

    def test_reduced_detector_keeps_its_reason_through_the_cache(self):
        detector = CachedNameDetector(ReducedNameDetector(HeuristicNameDetector(), "model_runtime"))
        self.assertEqual(detector.reduced, "model_runtime")
        self.assertIsNone(CachedNameDetector(HeuristicNameDetector()).reduced)


class ReducedServiceAnswerTest(unittest.TestCase):
    def test_service_answer_carries_the_reason(self):
        from privacy_guard.service.server import _BackgroundLoad, _find_names
        load = _BackgroundLoad(lambda: ReducedNameDetector(HeuristicNameDetector(), "model_files"))
        self.assertEqual(_find_names(load, "Nom : Sophie Martin")["reduced"], "model_files")

    def test_client_keeps_only_an_allowlisted_reason(self):
        from privacy_guard.service.channel import ServiceChannel
        from privacy_guard.service.client import ServiceClient
        client = ServiceClient(ServiceChannel(Path("unused")))
        for answer, expected in (({"findings": [], "reduced": "model_runtime"}, "model_runtime"),
                                 ({"findings": [], "reduced": "C:/Users/x"}, None), ({"findings": []}, None)):
            with self.subTest(answer=answer):
                client._request = lambda request, answer=answer: answer
                client.find_names("text")
                self.assertEqual(client.reduced, expected)


class ReducedToolOutputTest(unittest.TestCase):
    def protect(self, text, reduced):
        reports = []
        with tempfile.TemporaryDirectory() as temp:
            core = PrivacyCore(VaultStore(Path(temp), ReversingCipher()).session("s"), HeuristicNameDetector())
            result = protect_tool_output({**READ, "tool_response": {"content": text}}, core, reports.append,
                                         reduced)
        return (json.loads(result.stdout) if result.stdout else {}), reports

    def test_clean_document_still_warns_the_user(self):
        answer, reports = self.protect("Rendez-vous avec Lefebvre mardi.", lambda: "model_runtime")
        self.assertIn("détection des noms réduite", answer["systemMessage"])
        self.assertNotIn("hookSpecificOutput", answer)  # Nothing replaced: the result is unchanged.
        self.assertEqual(reports[0].record()["reduced"], "model_runtime")

    def test_full_model_adds_nothing(self):
        answer, reports = self.protect("Rendez-vous mardi.", lambda: None)
        self.assertEqual((answer, reports), ({}, []))


class ReducedNotificationTest(unittest.TestCase):
    def test_card_says_protection_is_reduced(self):
        with tempfile.TemporaryDirectory() as temp:
            queue, now = NotificationQueue(Path(temp)), time.time()
            queue.publish("s", None, ProtectionSummary({}, "C:/docs/notes.md", "model_runtime"), now)
            batch = queue.take_due(now + 60)[0]
        content = card_content(batch)
        self.assertEqual(content["headline"], "Protection réduite")
        self.assertIn("Détection des noms réduite", content["details"])
        self.assertIn("notes.md", banner_text(batch))


if __name__ == "__main__":
    unittest.main()
