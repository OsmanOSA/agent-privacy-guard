"""Installer upgrades preserve issued tokens; incompatible updates leave data intact."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from privacy_guard.__main__ import Installers, _install
from privacy_guard.claude_code.installer import ClaudeCodeInstaller
from privacy_guard.claude_code.vault_format import CURRENT_FORMAT, VaultCompatibilityError

EMAIL = "alice.martin@example.com"


@unittest.skipUnless(sys.platform == "win32", "Native Windows installer and DPAPI")
class InstallVaultTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name).resolve()
        self.claude = self.home / ".claude"
        self.claude.mkdir()
        self.guard = self.home / ".privacy-guard"
        self.marker = self.guard / "vault-format.json"
        self.installer = ClaudeCodeInstaller(self.claude, self.guard, Path(sys.executable))
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.installer.uninstall)
        self.installer.install()

    def call(self, text, tool="Bash"):
        payload = {"session_id": "retained-session", "hook_event_name": "PostToolUse",
                   "tool_name": tool, "tool_response": {"stdout": text}}
        env = {**os.environ, "HOME": str(self.home), "USERPROFILE": str(self.home)}
        result = subprocess.run([sys.executable, str(self.guard / "app")], input=json.dumps(payload),
                                capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertNotIn(EMAIL, result.stdout)
        return json.loads(result.stdout)["hookSpecificOutput"]["updatedToolOutput"]["stdout"]

    def snapshot(self):
        return {p.relative_to(self.guard).as_posix(): p.read_bytes()
                for p in (self.guard / "vault").rglob("*") if p.is_file()}

    def test_two_reinstalls_preserve_key_mappings_and_launcher_tokens(self):
        token = self.call(EMAIL)
        before = self.snapshot()
        settings = (self.claude / "settings.json").read_bytes()
        for _ in range(2):
            self.installer.install()
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(self.call(EMAIL), token)
            self.assertEqual((self.claude / "settings.json").read_bytes(), settings)
        self.assertEqual(json.loads(self.marker.read_text()), {"vault_format": CURRENT_FORMAT})

    def test_current_unmarked_installation_is_adopted_without_changing_tokens(self):
        token = self.call(EMAIL)
        before = self.snapshot()
        self.marker.unlink()
        self.installer.install()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.call(EMAIL), token)
        self.assertTrue(self.marker.is_file())

    def assert_refused_without_changes(self):
        vault = self.snapshot()
        app = {p.relative_to(self.guard).as_posix(): p.read_bytes()
               for p in (self.guard / "app").rglob("*.py")}
        settings = (self.claude / "settings.json").read_bytes()
        self.installer._service = Mock()
        with self.assertRaises(VaultCompatibilityError):
            self.installer.install()
        self.installer._service.stop.assert_not_called()
        self.assertEqual(self.snapshot(), vault)
        self.assertEqual({p.relative_to(self.guard).as_posix(): p.read_bytes()
                          for p in (self.guard / "app").rglob("*.py")}, app)
        self.assertEqual((self.claude / "settings.json").read_bytes(), settings)

    def test_different_format_is_refused_without_touching_app_settings_or_vault(self):
        self.call(EMAIL)
        self.marker.write_text(json.dumps({"vault_format": "future-incompatible-format"}))
        self.assert_refused_without_changes()

    def test_corrupted_marker_is_refused(self):
        self.call(EMAIL)
        self.marker.write_text("{invalid")
        self.assert_refused_without_changes()

    def test_recognized_v1_contract_is_adopted_without_rewriting_vault_data(self):
        self.call(EMAIL)
        before = self.snapshot()
        self.marker.write_text(json.dumps({"vault_format": "windows-dpapi-bound-personal-v1"}))
        self.installer.install()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(json.loads(self.marker.read_text()), {"vault_format": CURRENT_FORMAT})

    def test_unmarked_unknown_engine_is_refused(self):
        self.call(EMAIL)
        self.marker.unlink()
        (self.guard / "app/privacy_guard/core/bound_values.py").write_text("# unknown format\n")
        self.assert_refused_without_changes()

    def test_empty_vault_allows_a_new_format_contract(self):
        self.marker.write_text(json.dumps({"vault_format": "obsolete-format"}))
        self.installer.install()
        self.assertEqual(json.loads(self.marker.read_text()), {"vault_format": CURRENT_FORMAT})

    def test_cli_reports_incompatibility_without_installing_model_or_erasing_data(self):
        self.call(EMAIL)
        self.marker.write_text(json.dumps({"vault_format": "unknown"}))
        model = Mock()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = _install(Installers(self.installer, model), SimpleNamespace(model_source=None))
        self.assertEqual(code, 1)
        self.assertIn("vaults were kept", stdout.getvalue())
        self.assertNotIn(EMAIL, stdout.getvalue())
        model.install.assert_not_called()
        self.assertTrue(self.snapshot())
