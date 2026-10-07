"""Developer-tool words that are never a person's name on their own.

Claude Code sessions are full of "Claude", "Claude Code" and tool names (Read, Bash,
Grep...). One of them taken for a name used to be stored in the session and then
replaced in every later output, masking code such as read() or `claude --version`.
A name made only of these words is dropped; "Claude Moreau" is kept.

Known limit: a person called only "Claude", with no surname, is no longer detected.

Interface: is_tool_vocabulary(name) -> bool
"""

from __future__ import annotations

import re

_TERMS = frozenset({
    # The agent and its models.
    "anthropic", "claude", "code", "opus", "sonnet", "haiku", "fable",
    # Built-in tool names, as they appear in prompts, transcripts and documentation.
    "agent", "bash", "edit", "glob", "grep", "monitor", "multiedit", "notebookedit",
    "powershell", "read", "skill", "task", "todowrite", "webfetch", "websearch", "write",
})
_SEPARATORS = re.compile(r"[\s\-'’]+")


def is_tool_vocabulary(name: str) -> bool:
    """True when every word of the name is a developer-tool term."""
    words = [word for word in _SEPARATORS.split(name) if word]
    return bool(words) and all(word.lower() in _TERMS for word in words)
