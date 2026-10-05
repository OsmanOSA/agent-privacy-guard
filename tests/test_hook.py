import io
import json
import tempfile
import unittest
from pathlib import Path

from privacy_guard.claude_code import hook
from privacy_guard.claude_code.responses import EXIT_ALLOW, EXIT_BLOCK
from privacy_guard.core.vault import VaultStore
from tests.fakes import STRIPE_KEY, RecordingNameService, ReversingCipher

SESSION = "test-session"


class RecordingJournal:
    def __init__(self):
        self.events = []

    def record(self, event, tool):
        self.events.append((event, tool))


class BrokenJournal:
    def record(self, event, tool):
        raise OSError("disk full")


class HookTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vaults = VaultStore(Path(self._tmp.name), ReversingCipher())
        self.journal = RecordingJournal()
        self.names = RecordingNameService()

    def tearDown(self):
        self._tmp.cleanup()

    def run_hook(self, payload, journal=None):
        raw = payload if isinstance(payload, str) else json.dumps({"session_id": SESSION, **payload})
        stdout, stderr = io.StringIO(), io.StringIO()
        exit_code = hook.run(io.StringIO(raw), stdout, stderr, journal or self.journal, self.vaults, self.names)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def specific_output(self, stdout):
        return json.loads(stdout)["hookSpecificOutput"]

    def protect(self, text):
        _, stdout, _ = self.run_hook(
            {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_response": {"stdout": text}}
        )
        return self.specific_output(stdout)["updatedToolOutput"]["stdout"]

    def test_lets_clean_output_through_untouched(self):
        exit_code, stdout, _ = self.run_hook(
            {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_response": {"stdout": "PORT=3000"}}
        )

        self.assertEqual((exit_code, stdout), (EXIT_ALLOW, ""))
        self.assertEqual(self.journal.events, [("PostToolUse", "Bash")])

    def test_replaces_secrets_in_tool_output_and_keeps_its_shape(self):
        _, stdout, _ = self.run_hook(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_response": {"stdout": f"STRIPE_SECRET_KEY={STRIPE_KEY}", "stderr": "", "interrupted": False},
            }
        )

        output = self.specific_output(stdout)["updatedToolOutput"]
        self.assertEqual(set(output), {"stdout", "stderr", "interrupted"})
        self.assertNotIn(STRIPE_KEY, output["stdout"])
        self.assertIn("⟦STRIPE_SECRET_KEY:", output["stdout"])

    def test_restores_real_value_for_local_tool(self):
        token = self.protect(STRIPE_KEY)

        _, stdout, _ = self.run_hook(
            {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": f"echo {token}"}}
        )

        output = self.specific_output(stdout)
        self.assertEqual(output["updatedInput"], {"command": f"echo {STRIPE_KEY}"})
        self.assertNotIn("permissionDecision", output)

    def test_never_restores_for_sub_agents(self):
        token = self.protect(STRIPE_KEY)

        _, stdout, _ = self.run_hook(
            {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": {"prompt": f"use {token}"}}
        )

        self.assertEqual(stdout, "")

    def test_session_end_forgets_the_session_values(self):
        token_id = self.protect(STRIPE_KEY)[-9:-1]
        self.assertEqual(self.vaults.session(SESSION).lookup(token_id), STRIPE_KEY)

        exit_code, _, _ = self.run_hook({"hook_event_name": "SessionEnd", "reason": "prompt_input_exit"})

        self.assertEqual(exit_code, EXIT_ALLOW)
        self.assertIsNone(self.vaults.session(SESSION).lookup(token_id))

    def test_session_start_warms_the_name_service_up(self):
        exit_code, _, _ = self.run_hook({"hook_event_name": "SessionStart", "source": "startup"})

        self.assertEqual(exit_code, EXIT_ALLOW)
        self.assertTrue(self.names.started)

    def test_documents_go_through_the_name_service(self):
        _, stdout, _ = self.run_hook(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "C:/docs/cv.txt"},
                "tool_response": {"content": "Nom : Jean Dupont"},
            }
        )

        self.assertIn("Nom : Jean Dupont", self.names.queried)
        self.assertNotIn("Dupont", stdout)

    def test_code_never_reaches_the_name_service(self):
        _, stdout, _ = self.run_hook(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "C:/src/app.py"},
                "tool_response": {"content": "# Author: Jean Dupont"},
            }
        )

        self.assertEqual(self.names.queried, [])
        self.assertNotIn("Dupont", stdout)

    def test_blocks_when_payload_is_unreadable(self):
        exit_code, _, stderr = self.run_hook("not json")

        self.assertEqual(exit_code, EXIT_BLOCK)
        self.assertIn("Privacy Guard", stderr)

    def test_masks_tool_output_when_post_tool_use_fails(self):
        exit_code, stdout, _ = self.run_hook(
            {"hook_event_name": "PostToolUse", "tool_name": "Bash"}, journal=BrokenJournal()
        )

        output = self.specific_output(stdout)
        self.assertEqual(exit_code, EXIT_ALLOW)
        self.assertIn("Output masked", output["updatedToolOutput"])

    def test_fails_closed_without_session_id(self):
        exit_code, _, _ = self.run_hook(json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash"}))

        self.assertEqual(exit_code, EXIT_BLOCK)


if __name__ == "__main__":
    unittest.main()
