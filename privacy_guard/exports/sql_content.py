"""Restore SQL values inside string literals and comments, escaped for SQL.

A SQL script holds personal values in string literals ('Jean Dupont'). Restoring a
token there as plain text would break the statement on an apostrophe (O'Brien) or
change what it does. Values are therefore restored only where SQL holds data:

- single-quoted literals: unescaped, restored, then their quotes doubled again;
- comments: restored when the value cannot end the comment early.

Tokens anywhere else (identifiers, bare code) stay tokens: a value never becomes SQL
code. Standard SQL quoting only: MySQL backslash escapes and PostgreSQL dollar quoting
are not interpreted, so tokens inside dollar-quoted bodies stay tokens.

Interface: restore_sql(content, restore) -> str | None. None rejects the content (an
unterminated literal, identifier or comment), which leaves the file to the user.
"""

from __future__ import annotations

import re
from typing import Callable

# One alternative per SQL region; `unterminated` catches an opening without its end.
_REGION = re.compile(r"""
    (?P<literal>'(?:[^']|'')*')
  | (?P<identifier>"(?:[^"]|"")*"|`[^`]*`)
  | (?P<line_comment>--[^\r\n]*)
  | (?P<block_comment>/\*.*?\*/)
  | (?P<unterminated>['"`]|/\*)
""", re.VERBOSE | re.DOTALL)


def restore_sql(content: str, restore: Callable[[str], str]) -> str | None:
    restored, position = [], 0
    for region in _REGION.finditer(content):
        if region.lastgroup == "unterminated":
            return None
        restored.append(content[position:region.start()])  # Code between regions: unchanged.
        restored.append(_restore_region(region.lastgroup, region.group(), restore))
        position = region.end()
    restored.append(content[position:])
    return "".join(restored)


def _restore_region(kind: str, text: str, restore: Callable[[str], str]) -> str:
    if kind == "literal":
        value = restore(text[1:-1].replace("''", "'"))
        return "'" + value.replace("'", "''") + "'"
    if kind == "line_comment":
        value = restore(text)
        return text if "\n" in value or "\r" in value else value
    if kind == "block_comment":
        value = restore(text[2:-2])
        return text if "*/" in value else "/*" + value + "*/"
    return text
