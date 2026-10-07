"""Exercise automatic restoration through a launcher deployed only to a temporary home."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from privacy_guard.claude_code.installer import ClaudeCodeInstaller

EMAIL = "alice.martin@example.com"


@unittest.skipUnless(sys.platform == "win32", "Native Windows launcher")
class InstalledWriteCycleTest(unittest.TestCase):
    def test_separate_hook_processes_reuse_committed_names_only_in_same_session(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            claude, guard = home / '.claude', home / '.privacy-guard'
            claude.mkdir()
            installer = ClaudeCodeInstaller(claude, guard, Path(sys.executable))
            installer.install()
            try:
                env = {**os.environ, 'HOME': str(home), 'USERPROFILE': str(home)}

                def call(text, session='names'):
                    payload = dict(hook_event_name='PostToolUse', session_id=session, tool_name='Bash',
                                   tool_response={'stdout': text, 'stderr': '', 'isImage': False, 'interrupted': False})
                    reply = subprocess.run([sys.executable, str(guard / 'app')], input=json.dumps(payload),
                                           capture_output=True, text=True, encoding='utf-8', env=env, timeout=10)
                    self.assertEqual((reply.returncode, reply.stderr), (0, ''))
                    return json.loads(reply.stdout) if reply.stdout else {}

                initial = call('Nom : Alice')['hookSpecificOutput']['updatedToolOutput']['stdout']
                learned = call('alice')['hookSpecificOutput']['updatedToolOutput']['stdout']
                self.assertNotIn('alice', learned)
                self.assertEqual(call('Nom : Alice')['hookSpecificOutput']['updatedToolOutput']['stdout'], initial)
                self.assertEqual(call('alice', 'other-session'), {})
                self.assertNotIn(b'Alice', (guard / 'vault/names/personal.sqlite3').read_bytes())
                env_payload = dict(hook_event_name='SessionEnd', session_id='names')
                reply = subprocess.run([sys.executable, str(guard / 'app')], input=json.dumps(env_payload),
                                       capture_output=True, text=True, encoding='utf-8', env=env, timeout=10)
                self.assertEqual(reply.returncode, 0)
                self.assertFalse((guard / 'vault/names').exists())
                self.assertEqual(call('alice'), {})
            finally:
                installer.uninstall()

    def test_deployed_hook_restores_then_reprotects_without_export_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            claude = home / ".claude"
            claude.mkdir()
            guard = home / ".privacy-guard"
            installer = ClaudeCodeInstaller(claude, guard, Path(sys.executable))
            installer.install()
            try:
                env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}

                def call(payload):
                    result = subprocess.run([sys.executable, str(guard / "app")],
                                            input=json.dumps({"session_id": "cycle", **payload}),
                                            capture_output=True, text=True, encoding="utf-8", env=env)
                    self.assertEqual((result.returncode, result.stderr), (0, ""))
                    self.assertNotIn(EMAIL, result.stdout + result.stderr)
                    return json.loads(result.stdout)["hookSpecificOutput"] if result.stdout else {}

                initial = call({"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                "tool_response": {"stdout": EMAIL}})
                token = initial["updatedToolOutput"]["stdout"]
                for number in range(2):
                    target = home / f"chosen-{number}.txt"
                    args = {"file_path": str(target), "content": token}
                    self.assertEqual(call({"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": args}), {})
                    self.assertFalse(target.exists())
                    target.write_text(token, encoding="utf-8")
                    post = call({"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": args,
                                 "tool_response": {"filePath": str(target), "type": "create"}})
                    self.assertIn("restored", post["additionalContext"])
                    self.assertNotIn("updatedInput", post)
                    self.assertEqual(target.read_text(encoding="utf-8"), EMAIL)
                    reread = call({"hook_event_name": "PostToolUse", "tool_name": "Read",
                                   "tool_input": {"file_path": str(target)}, "tool_response": {"content": EMAIL}})
                    self.assertEqual(reread["updatedToolOutput"]["content"], token)
                self.assertFalse((guard / "export-policy.json").exists())
            finally:
                installer.uninstall()
