"""Keep session vaults across compatible installations and refuse unknown formats.

Interface: VaultCompatibility(guard_home, package_dir).check() / record() / clear().
No vault data is decrypted, migrated or deleted. An unmarked deployed version is
adopted only when its format-related sources exactly match the incoming package.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

# Change this identifier when record layout, token derivation or cipher changes.
CURRENT_FORMAT = "windows-dpapi-bound-personal-sqlite-v2"
READABLE_FORMATS = frozenset({"windows-dpapi-bound-personal-v1", CURRENT_FORMAT})
_FORMAT_FILES = (
    "core/bound_values.py", "core/category_policy.py", "core/privacy_core.py",
    "core/tokens.py", "core/vault.py", "core/cipher.py", "core/dpapi.py", "core/sqlite_records.py",
)


class VaultCompatibilityError(RuntimeError):
    """Installing would reuse session data whose format is not recognized."""


class VaultCompatibility:
    """Record a format contract outside the app and session directories."""

    def __init__(self, guard_home: Path, package_dir: Path) -> None:
        self._home, self._package = guard_home, package_dir
        self._marker = guard_home / "vault-format.json"

    def check(self) -> None:
        """Refuse incompatible nonempty vaults before any installation mutation."""
        if not any(path.is_file() for path in (self._home / "vault").rglob("*")):
            return
        try:
            if self._marker.exists():
                marker = json.loads(self._marker.read_text(encoding="utf-8"))
                compatible = (isinstance(marker, dict) and set(marker) == {"vault_format"}
                              and isinstance(marker["vault_format"], str)
                              and marker["vault_format"] in READABLE_FORMATS)
            else:
                deployed = self._home / "app" / self._package.name
                compatible = all((deployed / name).is_file()
                                 and (deployed / name).read_bytes() == (self._package / name).read_bytes()
                                 for name in _FORMAT_FILES)
        except (OSError, ValueError):
            compatible = False
        if not compatible:
            raise VaultCompatibilityError(
                "Existing session vaults have an unknown or incompatible format. "
                "Installation stopped; vaults were kept. Finish the old sessions "
                "before retrying, or explicitly uninstall if their mappings are no longer needed."
            )

    def record(self) -> None:
        """Publish the current contract atomically after a successful installation."""
        self._home.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=self._home, prefix=".vault-format-", delete=False) as pending:
            temporary = Path(pending.name)
            pending.write((json.dumps({"vault_format": CURRENT_FORMAT}) + "\n").encode("utf-8"))
            pending.flush()
            os.fsync(pending.fileno())
        try:
            os.replace(temporary, self._marker)
        finally:
            temporary.unlink(missing_ok=True)

    def clear(self) -> None:
        """Remove the contract during explicit uninstall, after vault deletion."""
        self._marker.unlink(missing_ok=True)
