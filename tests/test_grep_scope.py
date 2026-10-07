import unittest

from privacy_guard.claude_code.document_scope import is_document_read


def grep(content="", **tool_input):
    return {"tool_name": "Grep", "tool_input": {"pattern": "@", **tool_input},
            "tool_response": {"mode": "content", "numFiles": 0, "filenames": [], "content": content,
                              "numLines": 1, "totalLines": 1}}


class GrepScopeTest(unittest.TestCase):
    """Claude Code sends no filenames in content mode: lines and targets decide."""

    def test_lines_from_document_files_are_documents(self):
        for content in ("customers.csv:2:1,Camille,c@example.fr",
                        "src/app.py:3:x = 1\ndocs/notes.md:5:Rendez-vous",
                        "C:\\work\\lettre.txt:1:Madame",
                        "notes.md-4-context line"):
            with self.subTest(content=content):
                self.assertTrue(is_document_read(grep(content)))

    def test_lines_from_code_files_are_not_documents(self):
        for content in ("src/app.py:3:email = 'x@example.org'", "main.ts:1:// notes.md: see docs", ""):
            with self.subTest(content=content):
                self.assertFalse(is_document_read(grep(content)))

    def test_search_aimed_at_documents_is_a_document_read(self):
        # A single-file search prints lines without a filename prefix.
        self.assertTrue(is_document_read(grep("Rendez-vous avec", path="C:/work/notes.md")))
        self.assertTrue(is_document_read(grep("1,Camille", glob="*.csv")))
        self.assertTrue(is_document_read(grep("Madame", type="md")))

    def test_search_aimed_at_code_is_not(self):
        self.assertFalse(is_document_read(grep("x = 1", path="C:/work/src", glob="*.py", type="py")))

    def test_malformed_payload_is_not_a_document_read(self):
        self.assertFalse(is_document_read({"tool_name": "Grep", "tool_input": None, "tool_response": "x"}))


class McpScopeTest(unittest.TestCase):
    def test_mcp_results_are_documents(self):
        self.assertTrue(is_document_read({"tool_name": "mcp__crm__customer_card", "tool_input": {}}))

    def test_other_tool_names_are_not(self):
        for tool in ("WebSearch", "Agent", "mcp", None):
            with self.subTest(tool=tool):
                self.assertFalse(is_document_read({"tool_name": tool, "tool_input": {}}))


if __name__ == "__main__":
    unittest.main()
