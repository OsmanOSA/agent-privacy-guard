import io
import json
import tempfile
import unittest
from pathlib import Path

from privacy_guard.claude_code import hook
from privacy_guard.claude_code.responses import EXIT_ALLOW, EXIT_BLOCK
from privacy_guard.core.bound_values import BoundValues
from privacy_guard.core.vault import VaultStore
from tests.fakes import STRIPE_KEY, RecordingNameService, ReversingCipher

SESSION = "test-session"
EMAIL = "jean.dupont@example.com"


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
        self.export_root = Path(self._tmp.name).resolve() / "exports"
        self.export_root.mkdir()

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

    def test_write_keeps_personal_tokens_without_creating_an_output(self):
        token = self.protect(EMAIL)
        target = self.export_root / "clients.csv"
        exit_code, stdout, _ = self.run_hook(
            {"hook_event_name": "PreToolUse", "tool_name": "Write",
             "tool_input": {"file_path": str(target), "content": f"email\n{token}\n"}}
        )
        self.assertEqual((exit_code, stdout), (EXIT_ALLOW, ""))
        self.assertFalse(target.exists())

    def test_commands_edits_and_remote_tools_keep_personal_tokens(self):
        token = self.protect(EMAIL)
        for tool in ("Bash", "Edit", "MultiEdit", "NotebookEdit", "Agent", "mcp__remote__send"):
            with self.subTest(tool=tool):
                exit_code, stdout, _ = self.run_hook(
                    {"hook_event_name": "PreToolUse", "tool_name": tool,
                     "tool_input": {"command": f"echo {token}", "content": token}}
                )
                self.assertEqual((exit_code, stdout), (EXIT_ALLOW, ""))

    def test_outside_write_keeps_personal_tokens(self):
        token = self.protect(EMAIL)
        _, stdout, _ = self.run_hook(
            {"hook_event_name": "PreToolUse", "tool_name": "Write",
             "tool_input": {"file_path": str(Path(self._tmp.name) / "outside.csv"), "content": f"email\n{token}\n"}}
        )
        self.assertEqual(stdout, "")

    def test_write_does_not_read_the_vault_even_if_corrupted(self):
        token = self.protect(EMAIL)
        for path in (Path(self._tmp.name) / SESSION).iterdir():
            if path.name != "session.key":
                path.write_bytes(b"corrupted")
        exit_code, stdout, _ = self.run_hook(
            {"hook_event_name": "PreToolUse", "tool_name": "Write",
             "tool_input": {"file_path": str(self.export_root / "clients.csv"), "content": f"email\n{token}\n"}}
        )
        self.assertEqual((exit_code, stdout), (EXIT_ALLOW, ""))

    def test_never_restores_for_sub_agents(self):
        token = self.protect(EMAIL)

        _, stdout, _ = self.run_hook(
            {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": {"prompt": f"use {token}"}}
        )

        self.assertEqual(stdout, "")

    def test_never_restores_redacted_secret_in_local_tool_arguments(self):
        marker = self.protect(STRIPE_KEY)

        exit_code, stdout, _ = self.run_hook(
            {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": f"echo {marker}"}}
        )

        self.assertEqual((exit_code, stdout), (EXIT_ALLOW, ""))
        self.assertEqual(marker, "⟦STRIPE_SECRET_KEY:REDACTED⟧")

    def test_session_end_forgets_the_session_values(self):
        token_id = self.protect(EMAIL)[-9:-1]
        self.assertEqual(BoundValues(self.vaults.session(SESSION)).lookup("email", token_id), EMAIL)

        exit_code, _, _ = self.run_hook({"hook_event_name": "SessionEnd", "reason": "prompt_input_exit"})

        self.assertEqual(exit_code, EXIT_ALLOW)
        self.assertIsNone(BoundValues(self.vaults.session(SESSION)).lookup("email", token_id))

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
        self.assertIn("Output masked", output["updatedToolOutput"]["stdout"])
        self.assertFalse(json.loads(stdout)["continue"])

    def test_fails_closed_without_session_id(self):
        exit_code, _, _ = self.run_hook(json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash"}))

        self.assertEqual(exit_code, EXIT_BLOCK)


if __name__ == "__main__":
    unittest.main()
