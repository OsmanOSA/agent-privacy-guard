import unittest

from privacy_guard.claude_code.document_scope import is_document_read


def read(path):
    return {"tool_name": "Read", "tool_input": {"file_path": path}}


def bash(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


class DocumentScopeTest(unittest.TestCase):
    def test_document_files_are_documents(self):
        for path in ("C:/docs/cv.txt", "/home/me/notes.MD", "contrat.pdf", "lettre.docx", "clients.csv"):
            self.assertTrue(is_document_read(read(path)), path)

    def test_code_and_config_are_not_documents(self):
        for path in ("app.py", "index.ts", ".env", "settings.json", "Dockerfile"):
            self.assertFalse(is_document_read(read(path)), path)

    def test_shell_commands_naming_a_document(self):
        self.assertTrue(is_document_read(bash("cat playground/fiche_client.txt")))
        self.assertFalse(is_document_read(bash("npm test")))

    def test_other_tools_are_not_documents(self):
        self.assertFalse(is_document_read({"tool_name": "Grep", "tool_input": {"pattern": "cv.txt"}}))


if __name__ == "__main__":
    unittest.main()
