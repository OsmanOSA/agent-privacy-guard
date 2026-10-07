"""Restore personal values inside the text cells of an Excel workbook (.xlsx, .xlsm).

Agents build workbooks with scripts; values they only know as session tokens end up
as tokens in the cells. A workbook is a ZIP of XML parts: text cells live in
`<t>` elements of the shared strings and, for inline strings, of the worksheets.
Only those elements change. Formulas (`<f>`), numbers (`<v>`), styles and every
other part are copied byte for byte, so a restored value can never become a formula.

Interface: restore_xlsx(data, restore) -> bytes | None. None rejects the content
(not a workbook, too large once decompressed, undecodable XML).
"""

from __future__ import annotations

import io
import re
import zipfile
from typing import Callable
from xml.sax.saxutils import escape, unescape

# Decompressed size limit: a small archive can expand enormously (ZIP bomb).
MAX_UNCOMPRESSED_BYTES = 64 * 1024 * 1024
_TEXT_PARTS = re.compile(r"xl/(?:sharedStrings|worksheets/sheet\d+)\.xml")
_TEXT = re.compile(r"(<t(?:\s[^>]*)?>)([^<]*)(</t>)")
_ENTITIES = {"&quot;": '"', "&apos;": "'"}


def restore_xlsx(data: bytes, restore: Callable[[str], str]) -> bytes | None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as source:
            entries = source.infolist()
            if ("xl/workbook.xml" not in source.namelist()
                    or sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED_BYTES):
                return None
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w") as target:
                target.comment = source.comment
                for entry in entries:
                    content = source.read(entry)
                    if _TEXT_PARTS.fullmatch(entry.filename):
                        content = _restore_part(content.decode("utf-8"), restore).encode("utf-8")
                    target.writestr(entry, content)  # Same name, date and compression.
        return output.getvalue()
    except (zipfile.BadZipFile, zipfile.LargeZipFile, UnicodeDecodeError, OSError, EOFError):
        return None


def _restore_part(xml: str, restore: Callable[[str], str]) -> str:
    def text_element(match: re.Match) -> str:
        value = unescape(match.group(2), _ENTITIES)
        restored = restore(value)
        return match.group(0) if restored == value else match.group(1) + escape(restored) + match.group(3)
    return _TEXT.sub(text_element, xml)
