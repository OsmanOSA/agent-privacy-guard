import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from privacy_guard.claude_code import registration
from privacy_guard.claude_code.installer import ClaudeCodeInstaller, ClaudeCodeNotFoundError
from tests.fakes import STRIPE_KEY

ORIGINAL_SETTINGS = {"model": "opus", "enabledPlugins": {"some-plugin": True}}


class InstallerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.claude_dir = self.home / ".claude"
        self.claude_dir.mkdir()
        self.settings_path = self.claude_dir / "settings.json"
        self.settings_path.write_text(json.dumps(ORIGINAL_SETTINGS), encoding="utf-8")
        self.installer = ClaudeCodeInstaller(self.claude_dir, self.home / ".privacy-guard", Path(sys.executable))

    def tearDown(self):
        # Stops the background service the installed hook may have started.
        self.installer.uninstall()
        self._tmp.cleanup()

    def test_install_protects_every_event(self):
        self.installer.install()

        self.assertEqual(self.installer.status(), {event: True for event in registration.HOOK_EVENTS})

    def test_installed_hook_runs_end_to_end(self):
        self.installer.install()

        result = self._run_installed_hook({"hook_event_name": "PreToolUse", "tool_name": "Read"})

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_installed_hook_reads_non_latin_content(self):
        # "Ё" contains byte 0x81, unreadable in cp1252 (the Windows default encoding).
        self.installer.install()

        result = self._run_installed_hook(
            {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_response": "Ёlise, café"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "", "the tool output must not be masked")

    def test_installed_hook_protects_secrets(self):
        self.installer.install()

        result = self._run_installed_hook(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Read",
                "tool_response": f"STRIPE_SECRET_KEY={STRIPE_KEY}",
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("sk_live_", result.stdout)
        self.assertIn("⟦STRIPE_SECRET_KEY:", result.stdout)

    def test_installed_hook_keeps_tokens_even_with_export_configuration(self):
        export_root = self.home / "exports"
        export_root.mkdir()
        guard_home = self.home / ".privacy-guard"
        guard_home.mkdir()
        (guard_home / "export-policy.json").write_text(
            json.dumps({"version": 1, "root": str(export_root.resolve())}), encoding="utf-8"
        )
        self.installer.install()
        email = "jean.dupont@example.com"
        protected = self._run_installed_hook(
            {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_response": email}
        )
        self.assertEqual(protected.returncode, 0, protected.stderr)
        token = json.loads(protected.stdout)["hookSpecificOutput"]["updatedToolOutput"]

        restored = self._run_installed_hook(
            {"hook_event_name": "PreToolUse", "tool_name": "Write",
             "tool_input": {"file_path": str((export_root / "clients.csv").resolve()), "content": f"email\n{token}\n"}}
        )

        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(restored.stdout, "")
        self.assertNotIn(email, restored.stdout + restored.stderr)
        self.assertFalse((export_root / "clients.csv").exists(), "a hook transforms arguments; it does not write the CSV")

    def test_uninstall_restores_original_settings(self):
        self.installer.install()

        self.installer.uninstall()

        self.assertEqual(json.loads(self.settings_path.read_text(encoding="utf-8")), ORIGINAL_SETTINGS)
        self.assertFalse((self.home / ".privacy-guard" / "app").exists())

    def test_install_keeps_empty_vault_directories_and_uninstall_purges_them(self):
        stale_vault = self.home / ".privacy-guard" / "vault" / "old-session"
        stale_vault.mkdir(parents=True)

        self.installer.install()
        self.assertTrue(stale_vault.exists())

        self.installer.uninstall()
        self.assertFalse(stale_vault.exists())
        self.assertFalse((self.home / ".privacy-guard" / "vault-format.json").exists())

    def test_consecutive_changes_keep_every_backup(self):
        first = self.installer.install()

        second = self.installer.uninstall()

        self.assertNotEqual(first, second)
        self.assertTrue(first.exists() and second.exists())

    def test_install_fails_without_claude_code(self):
        installer = ClaudeCodeInstaller(self.home / "absent", self.home / ".privacy-guard", Path(sys.executable))

        with self.assertRaises(ClaudeCodeNotFoundError):
            installer.install()

    def _run_installed_hook(self, payload):
        settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
        handler = settings["hooks"]["PreToolUse"][0]["hooks"][0]
        # HOME and USERPROFILE point to the temp dir so the journal never writes to the real home.
        env = {**os.environ, "HOME": str(self.home), "USERPROFILE": str(self.home)}
        # Exec form: Claude Code starts the interpreter directly, with no shell in between.
        return subprocess.run(
            [handler["command"], *handler["args"]],
            input=json.dumps({"session_id": "test-session", **payload}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )


if __name__ == "__main__":
    unittest.main()
