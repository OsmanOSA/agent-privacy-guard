"""Local files whose personal values come back on disk after the agent writes them.

The agent works on session tokens. Without restoration, rewriting a file it read
(a fixture in user_service.py, a contact in settings.yaml) would leave tokens in place
of the user's data. A successful Write of one of these files gets the session's
original values back (exports/written_file.py); an Edit carrying placeholders is
refused in favour of that Write (claude_code/edit_policy.py).

Text formats only: documents, source code and configuration. Values go back exactly
as they were read, without escaping for the host language. Spreadsheet formats other
than CSV (whose body cells get dedicated quoting) and binary formats are excluded.

Interface:
    is_restorable(path) -> bool
"""

from __future__ import annotations

from pathlib import PurePath, PureWindowsPath

_DOCUMENTS = {".txt", ".md", ".markdown", ".rst", ".csv"}
_SOURCE_CODE = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".java", ".kt", ".kts", ".cs",
    ".go", ".rs", ".rb", ".php", ".swift", ".scala", ".c", ".h", ".cc", ".cpp", ".hpp", ".r",
    ".lua", ".pl", ".dart", ".vue", ".svelte", ".sql", ".sh", ".bash", ".zsh", ".ps1", ".psm1",
    ".bat", ".cmd", ".html", ".htm", ".css", ".scss",
}
_CONFIGURATION = {
    ".json", ".jsonc", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".properties", ".env", ".xml",
}
RESTORABLE_EXTENSIONS = frozenset(_DOCUMENTS | _SOURCE_CODE | _CONFIGURATION)


def is_restorable(path: str | PurePath) -> bool:
    """Tells whether a written file of this name gets its personal values back."""
    name = PureWindowsPath(path).name.lower()
    # .env, .env.local, .env.production: dotenv files are named, not suffixed.
    if name == ".env" or name.startswith(".env."):
        return True
    return PureWindowsPath(name).suffix in RESTORABLE_EXTENSIONS
