import sys
import tempfile
import threading
import time
import unittest
import warnings
from multiprocessing.connection import Client
from pathlib import Path

from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.service.channel import ServiceChannel
from privacy_guard.service.client import ServiceClient
from privacy_guard.service.server import serve


class ServiceTest(unittest.TestCase):
    """Starts a real background service in a temp run directory."""

    def setUp(self):
        # The service is launched detached on purpose: Python warns that it outlives its Popen object.
        warnings.simplefilter("ignore", ResourceWarning)
        self._tmp = tempfile.TemporaryDirectory()
        self.channel = ServiceChannel(Path(self._tmp.name) / "run")
        # The system Python has no NER model: the service falls back to the instant heuristic.
        self.client = ServiceClient(self.channel, python=Path(sys.executable))

    def tearDown(self):
        self.client.stop()
        time.sleep(0.2)  # let the service process exit before deleting its files
        self._tmp.cleanup()

    def test_starts_on_first_use_and_answers(self):
        findings = self.client.find_names("Nom : Jean Dupont")

        self.assertEqual([(f.kind, f.start, f.end) for f in findings], [("person_name", 6, 17)])

    def test_later_calls_reuse_the_running_service(self):
        self.client.find_names("warm up")

        started = time.perf_counter()
        for _ in range(20):
            self.client.find_names("Madame Marie Martin")
        average_ms = (time.perf_counter() - started) / 20 * 1000

        self.assertLess(average_ms, 50)

    def test_survives_a_client_that_disconnects_mid_request(self):
        self.client.find_names("warm up")
        rude = Client(self.channel.address, self.channel.family, authkey=self.channel.authkey())
        rude.close()

        self.assertEqual(len(self.client.find_names("M. Dupont")), 1)

    def test_stop_reports_whether_a_service_was_running(self):
        self.assertFalse(self.client.stop())
        self.client.find_names("warm up")

        self.assertTrue(self.client.stop())

    def test_fallback_is_logged_when_the_model_is_missing(self):
        self.client.find_names("warm up")

        log = (self.channel.run_dir.parent / "logs" / "service.log").read_text(encoding="utf-8")
        self.assertIn("heuristic only", log)


class SlowDetector:
    """A detector that takes a while to load, like the NER model."""

    def __init__(self):
        time.sleep(1.0)
        self._inner = HeuristicNameDetector()

    def find_names(self, text):
        return self._inner.find_names(text)


class BackgroundLoadTest(unittest.TestCase):
    """Runs the server in a thread of the test process, with a slow detector."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.channel = ServiceChannel(Path(self._tmp.name) / "run")
        self.client = ServiceClient(self.channel)
        self.server = threading.Thread(target=serve, args=(self.channel, SlowDetector, 3600), daemon=True)
        self.server.start()
        time.sleep(0.2)  # the channel opens right away; the detector is still loading

    def tearDown(self):
        self.client.stop()
        self.server.join(timeout=5)
        self._tmp.cleanup()

    def test_answers_while_loading_then_waits_for_the_detector(self):
        self.assertFalse(self.client.is_ready())

        findings = self.client.find_names("Madame Marie Martin")

        self.assertEqual(len(findings), 1)
        self.assertTrue(self.client.is_ready())


if __name__ == "__main__":
    unittest.main()
