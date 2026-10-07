import unittest

from privacy_guard.claude_code.tool_failures import MASKED, masked_result

# Result shapes captured from Claude Code 2.1.292 hook payloads.
GREP_CONTENT = {"mode": "content", "numFiles": 0, "filenames": [], "content": "notes.md:1:secret line",
                "numLines": 1, "totalLines": 1}
GREP_FILES = {"mode": "files_with_matches", "filenames": ["notes.md"], "numFiles": 1, "totalFiles": 1}
GREP_COUNT = {"mode": "count", "numFiles": 1, "filenames": [], "content": "notes.md:1", "numMatches": 1}
GLOB = {"filenames": ["cv_jean.md"], "durationMs": 3, "numFiles": 1, "truncated": False,
        "totalMatches": 1, "countIsComplete": True}


class SearchResultMaskTest(unittest.TestCase):
    def test_current_grep_shapes_are_masked(self):
        for original in (GREP_CONTENT, GREP_FILES, GREP_COUNT):
            with self.subTest(mode=original["mode"]):
                masked = masked_result("Grep", original)
                self.assertEqual(set(masked), set(original))
                self.assertEqual(masked["filenames"], [])
                if "content" in original:
                    self.assertEqual(masked["content"], MASKED)

    def test_current_glob_shape_is_masked(self):
        masked = masked_result("Glob", GLOB)
        self.assertEqual((masked["filenames"], masked["truncated"]), ([], False))

    def test_unknown_text_field_refuses_replacement(self):
        self.assertIsNone(masked_result("Grep", {**GREP_CONTENT, "preview": "notes.md: secret"}))


if __name__ == "__main__":
    unittest.main()
