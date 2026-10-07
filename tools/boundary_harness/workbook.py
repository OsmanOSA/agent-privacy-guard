"""A minimal .xlsx workbook built with the standard library, for synthetic fixtures.

Interface: workbook(rows) -> bytes. Every cell is a shared string, like spreadsheets
saved by Excel; one sheet named "Clients".
"""

from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>"""
_ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
_WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Clients" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
_WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>
</Relationships>"""
_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def workbook(rows: list[list[str]]) -> bytes:
    strings = list(dict.fromkeys(cell for row in rows for cell in row))
    sheet_rows = "".join(
        f'<row r="{r}">' + "".join(f'<c r="{chr(65 + c)}{r}" t="s"><v>{strings.index(cell)}</v></c>'
                                   for c, cell in enumerate(row)) + "</row>"
        for r, row in enumerate(rows, start=1))
    sheet = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="{_MAIN}"><sheetData>{sheet_rows}</sheetData></worksheet>'
    shared = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<sst xmlns="{_MAIN}" count="{len(strings)}" '
              f'uniqueCount="{len(strings)}">' + "".join(f"<si><t>{escape(s)}</t></si>" for s in strings) + "</sst>")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in (("[Content_Types].xml", _CONTENT_TYPES), ("_rels/.rels", _ROOT_RELS),
                           ("xl/workbook.xml", _WORKBOOK), ("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS),
                           ("xl/worksheets/sheet1.xml", sheet), ("xl/sharedStrings.xml", shared)):
            archive.writestr(name, text)
    return output.getvalue()
