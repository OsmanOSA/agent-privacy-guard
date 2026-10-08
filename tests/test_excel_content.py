"""Workbook restoration: text cells only, XML-escaped, formulas untouched."""

import io
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from boundary_harness.workbook import workbook  # noqa: E402
from privacy_guard.exports import excel_content  # noqa: E402
from privacy_guard.exports.excel_content import restore_xlsx  # noqa: E402

NAME = "⟦PERSON_NAME:ABCDEF12⟧"
FORMULA_SHEET = ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                 f'<row r="1"><c r="A1" t="str"><f>CONCAT("{NAME}")</f><v>{NAME}</v></c>'
                 f'<c r="B1" t="inlineStr"><is><t xml:space="preserve">{NAME} </t></is></c></row>'
                 '</sheetData></worksheet>')


def restore(text):
    return text.replace(NAME, "Ana & <Bob> O'Hara")


def part(data, name):
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        return book.read(name).decode("utf-8")


class ExcelContentTest(unittest.TestCase):
    def test_shared_strings_are_restored_and_escaped(self):
        restored = restore_xlsx(workbook([["Nom"], [NAME]]), restore)
        self.assertIn("<t>Ana &amp; &lt;Bob&gt; O'Hara</t>", part(restored, "xl/sharedStrings.xml"))
        self.assertIn("<t>Nom</t>", part(restored, "xl/sharedStrings.xml"))

    def test_formulas_and_values_keep_tokens_inline_strings_are_restored(self):
        source = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(workbook([["Nom"]]))) as book, zipfile.ZipFile(source, "w") as copy:
            for entry in book.infolist():
                content = FORMULA_SHEET if entry.filename == "xl/worksheets/sheet1.xml" else book.read(entry)
                copy.writestr(entry, content)
        sheet = part(restore_xlsx(source.getvalue(), restore), "xl/worksheets/sheet1.xml")
        self.assertIn(f'<f>CONCAT("{NAME}")</f><v>{NAME}</v>', sheet)
        self.assertIn('<t xml:space="preserve">Ana &amp; &lt;Bob&gt; O\'Hara </t>', sheet)

    def test_other_parts_and_entry_order_are_unchanged(self):
        source = workbook([["Nom"], [NAME]])
        restored = restore_xlsx(source, restore)
        with zipfile.ZipFile(io.BytesIO(source)) as before, zipfile.ZipFile(io.BytesIO(restored)) as after:
            self.assertEqual(before.namelist(), after.namelist())
            self.assertEqual(before.read("xl/workbook.xml"), after.read("xl/workbook.xml"))

    def test_non_workbooks_and_oversized_archives_are_rejected(self):
        self.assertIsNone(restore_xlsx(b"not a zip", restore))
        plain = io.BytesIO()
        with zipfile.ZipFile(plain, "w") as archive:
            archive.writestr("readme.txt", NAME)
        self.assertIsNone(restore_xlsx(plain.getvalue(), restore))
        with patch.object(excel_content, "MAX_UNCOMPRESSED_BYTES", 100):
            self.assertIsNone(restore_xlsx(workbook([[NAME]]), restore))


if __name__ == "__main__":
    unittest.main()
