import io
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from privacy_guard.claude_code import hook
from privacy_guard.claude_code.deadline import ANSWER_DEADLINE_SECONDS, AnswerGate
from privacy_guard.claude_code.registration import HOOK_TIMEOUT_SECONDS
from privacy_guard.claude_code.responses import HookResult
from privacy_guard.core.vault import VaultStore
from tests.fakes import RecordingNameService, ReversingCipher

SECRET_LINE = "Contact : Camille Lefebvre <c.lefebvre@example.org>"


class StalledNameService(RecordingNameService):
    """A name service that answers only after the hook's deadline."""

    def find_names(self, text):
        time.sleep(0.6)
        return super().find_names(text)


class FailureJournal:
    def __init__(self):
        self.failures = []

    def record(self, event, tool):
        pass

    def record_failure(self, event, tool, stage, category):
        self.failures.append((event, tool, stage, category))


class AnswerGateTest(unittest.TestCase):
    def test_only_the_first_answer_is_written(self):
        written = []
        gate = AnswerGate(written.append)
        self.assertTrue(gate.answer(HookResult(0, "first")))
        self.assertFalse(gate.answer(HookResult(2, "second")))
        self.assertEqual((written, gate.written.stdout), ([HookResult(0, "first")], "first"))

    def test_deadline_writes_the_fallback_and_ends_the_process(self):
        written, exited = [], threading.Event()
        gate = AnswerGate(written.append)
        with patch("os._exit", side_effect=lambda code: exited.set()):
            gate.deadline(0.05, lambda: HookResult(2, "fallback"))
            self.assertTrue(exited.wait(2))
        self.assertEqual(written, [HookResult(2, "fallback")])

    def test_cancelled_deadline_never_fires(self):
        written = []
        gate = AnswerGate(written.append)
        gate.deadline(0.05, lambda: HookResult(2, "fallback")).cancel()
        time.sleep(0.15)
        self.assertEqual(written, [])

    def test_deadline_leaves_time_before_claude_code_kills_the_hook(self):
        self.assertLessEqual(ANSWER_DEADLINE_SECONDS, HOOK_TIMEOUT_SECONDS - 5)
        # Cold start of the name service: connection (8 s) plus first answer (25 s).
        self.assertGreater(ANSWER_DEADLINE_SECONDS, 33)


class HookDeadlineTest(unittest.TestCase):
    def test_stalled_inspection_answers_masked_before_the_timeout(self):
        payload = {"session_id": "s", "hook_event_name": "PostToolUse", "tool_name": "Read",
                   "tool_input": {"file_path": "notes.md"},
                   "tool_response": {"type": "text", "file": {"filePath": "notes.md", "content": SECRET_LINE,
                                                               "numLines": 1, "startLine": 1, "totalLines": 1}}}
        stdout, stderr, journal = io.StringIO(), io.StringIO(), FailureJournal()
        with tempfile.TemporaryDirectory() as temp, patch("os._exit"):
            vaults = VaultStore(Path(temp), ReversingCipher())
            hook.run(io.StringIO(json.dumps(payload)), stdout, stderr, journal, vaults,
                     StalledNameService(), deadline_seconds=0.1)
        answer = json.loads(stdout.getvalue())
        self.assertNotIn("Camille", stdout.getvalue())
        self.assertFalse(answer["continue"])
        self.assertEqual(journal.failures, [("PostToolUse", "Read", "answer_deadline", "timeout")])


if __name__ == "__main__":
    unittest.main()
