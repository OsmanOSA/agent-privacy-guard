"""Workbooks named by a successful shell command get the session's values back."""

import io
import json
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from boundary_harness.workbook import workbook  # noqa: E402
from privacy_guard.claude_code.workbook_restoration import named_workbooks, process_shell_result  # noqa: E402
from privacy_guard.exports.written_workbook import WorkbookRestorer  # noqa: E402
from tests.written_file_fixtures import EMAIL, WrittenFileTestCase  # noqa: E402

CWD = "C:\\work\\project"


def shared_strings(path):
    with zipfile.ZipFile(path) as book:
        return book.read("xl/sharedStrings.xml").decode("utf-8")


class NamedWorkbooksTest(unittest.TestCase):
    def test_bare_quoted_and_absolute_paths(self):
        command = ("python -c \"import pandas; df.to_excel('out/report.xlsx')\" && "
                   'copy "C:\\data\\Clients 2026.XLSM" backup.xlsx')
        self.assertEqual(named_workbooks(command, CWD),
                         [str(Path(CWD) / "out/report.xlsx"), "C:\\data\\Clients 2026.XLSM", str(Path(CWD) / "backup.xlsx")])

    def test_other_files_and_missing_cwd(self):
        self.assertEqual(named_workbooks("cat notes.xlsx.txt report.xls", CWD), [])
        self.assertEqual(named_workbooks("python make.py report.xlsx", None), [])
        self.assertEqual(named_workbooks(None, CWD), [])


class ShellResultTest(WrittenFileTestCase):
    def payload(self, command, **extra):
        return {"hook_event_name": "PostToolUse", "tool_name": "Bash", "cwd": str(self.home),
                "tool_input": {"command": command, **extra}, "tool_response": {"stdout": "", "stderr": ""}}

    def context(self, result):
        return json.loads(result.stdout)["hookSpecificOutput"].get("additionalContext", "") if result.stdout else ""

    def test_restoration_is_reported_without_values(self):
        restorer = Mock(restore=Mock(return_value=True))
        result = process_shell_result(self.payload("python make.py report.xlsx"), self.core, restorer)
        restorer.restore.assert_called_once_with(str(self.home / "report.xlsx"), self.core.restore)
        self.assertIn("restored in the local file", self.context(result))

    def test_failure_is_reported_and_background_commands_are_skipped(self):
        failing = Mock(restore=Mock(side_effect=OSError("locked")))
        result = process_shell_result(self.payload("python make.py report.xlsx"), self.core, failing)
        self.assertIn("restoration failed", self.context(result))
        idle = Mock()
        process_shell_result(self.payload("python make.py report.xlsx", run_in_background=True), self.core, idle)
        idle.restore.assert_not_called()

    @unittest.skipUnless(sys.platform == "win32", "Native Windows restoration")
    def test_workbook_on_disk_gets_its_values_back(self):
        token = self.core.protect(EMAIL)
        path = self.home / "report.xlsx"
        path.write_bytes(workbook([["Email"], [token]]))
        self.assertTrue(WorkbookRestorer().restore(str(path), self.core.restore))
        self.assertIn(f"<t>{EMAIL}</t>", shared_strings(path))
        self.assertNotIn(token, shared_strings(path))
        # A second pass finds nothing left to restore.
        self.assertFalse(WorkbookRestorer().restore(str(path), self.core.restore))

    def test_missing_and_non_workbook_paths_are_ignored(self):
        restorer = WorkbookRestorer(files=Mock())
        for path in (str(self.home / "absent.xlsx"), str(self.home / "notes.txt"), "relative.xlsx"):
            with self.subTest(path=path):
                self.assertFalse(restorer.restore(path, Mock()))


if __name__ == "__main__":
    unittest.main()
