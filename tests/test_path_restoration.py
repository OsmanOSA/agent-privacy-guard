import io
import json
import tempfile
import unittest
from pathlib import Path

from privacy_guard.claude_code import hook
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from tests.fakes import RecordingNameService, ReversingCipher

SESSION = "paths"


class PathRestorationTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.vaults = VaultStore(Path(temporary.name), ReversingCipher())
        core = PrivacyCore(self.vaults.session(SESSION), HeuristicNameDetector())
        self.token = core.protect("Nom : Camille Lefebvre").removeprefix("Nom : ")
        self.real = "C:/docs/cv_Camille Lefebvre.md"
        self.masked = self.real.replace("Camille Lefebvre", self.token)

    def run_hook(self, tool, arguments, session=SESSION):
        payload = {"hook_event_name": "PreToolUse", "session_id": session, "tool_name": tool, "tool_input": arguments}
        stdout = io.StringIO()
        hook.run(io.StringIO(json.dumps(payload)), stdout, io.StringIO(), _Journal(), self.vaults,
                 RecordingNameService())
        return json.loads(stdout.getvalue())["hookSpecificOutput"] if stdout.getvalue() else {}

    def test_file_tools_receive_the_real_path(self):
        for tool, key in (("Read", "file_path"), ("Write", "file_path"), ("Glob", "path"), ("Grep", "path")):
            with self.subTest(tool=tool):
                output = self.run_hook(tool, {key: self.masked, "pattern": "*"})
                self.assertEqual(output["updatedInput"][key], self.real)
                self.assertNotIn("permissionDecision", output)

    def test_shell_commands_never_get_originals(self):
        output = self.run_hook("Bash", {"command": f"cat '{self.masked}'"})
        self.assertNotIn("Camille", json.dumps(output))

    def test_other_sessions_and_plain_paths_are_unchanged(self):
        self.assertEqual(self.run_hook("Read", {"file_path": self.masked}, session="other"), {})
        self.assertEqual(self.run_hook("Read", {"file_path": "C:/docs/notes.md"}), {})


class _Journal:
    def record(self, event, tool):
        pass


if __name__ == "__main__":
    unittest.main()
