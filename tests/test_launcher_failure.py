"""Run an isolated broken installation through native Python, without its engine."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from privacy_guard.claude_code.installer import LAUNCHER_FILE


class LauncherFailureTest(unittest.TestCase):
    def call(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory) / "app"
            package = app / "privacy_guard"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("")
            shutil.copyfile(LAUNCHER_FILE, app / "__main__.py")
            reply = subprocess.run([sys.executable, str(app)], cwd=directory,
                                  input=json.dumps(payload), capture_output=True,
                                  text=True, encoding="utf-8", timeout=10,
                                  env={**os.environ, 'HOME': directory, 'USERPROFILE': directory})
            row = json.loads((Path(directory) / '.privacy-guard/logs/failures.jsonl').read_text().splitlines()[-1])
            self.assertEqual((row['stage'], row['category']), ('launcher_init', 'installation_unavailable'))
            self.assertNotIn('alice@example.com', json.dumps(row))
            return reply

    def test_broken_pretool_installation_blocks_before_execution(self):
        reply = self.call({"hook_event_name": "PreToolUse"})
        self.assertEqual(reply.returncode, 0)
        output = json.loads(reply.stdout)["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertIn("Privacy Guard", output["permissionDecisionReason"])

    def test_broken_posttool_installation_uses_native_stop(self):
        for event in ("PostToolUse", "PostToolUseFailure"):
            with self.subTest(event=event):
                reply = self.call({"hook_event_name": event, "tool_response": "alice@example.com"})
                self.assertEqual((reply.returncode, reply.stderr), (0, ""))
                response = json.loads(reply.stdout)
                self.assertFalse(response["continue"])
                self.assertNotIn("alice@example.com", reply.stdout)
                self.assertNotIn("hookSpecificOutput", response)

    def test_malformed_event_does_not_break_corruption_response(self):
        reply = self.call({"hook_event_name": {"unexpected": "value"}})
        self.assertEqual(reply.returncode, 2)
