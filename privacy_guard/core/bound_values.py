"""Store personal mappings bound to their category inside the encrypted vault.

Interface: BoundValues(vault).store(kind, identifier, value) / lookup(kind, identifier).
Legacy unbound files are neither read nor migrated. Category and value are
encrypted together; relabeling a token never selects another category's record.
"""

from __future__ import annotations

import json
import re

from privacy_guard.core.category_policy import Mode, mode_for
from privacy_guard.core.vault import SessionVault, VaultError

_IDENTIFIER = re.compile(r"[0-9A-F]{8}")


class BoundValues:
    """Keep the token's category, identifier and value in one encrypted record."""

    def __init__(self, vault: SessionVault) -> None:
        self._vault = vault

    def store(self, kind: str, identifier: str, value: str) -> None:
        key = _key(kind, identifier)
        if not isinstance(value, str):
            raise VaultError("Invalid personal mapping value")
        record = {"version": 1, "kind": kind, "identifier": identifier, "value": value}
        self._vault.store(key, json.dumps(record, ensure_ascii=False, separators=(",", ":")))

    def lookup(self, kind: str, identifier: str) -> str | None:
        if mode_for(kind) is not Mode.PSEUDONYMIZE:
            return None
        encoded = self._vault.lookup(_key(kind, identifier))
        if encoded is None:
            return None
        try:
            record = json.loads(encoded)
        except (TypeError, ValueError):
            raise VaultError("Invalid bound personal mapping") from None
        if (not isinstance(record, dict) or set(record) != {"version", "kind", "identifier", "value"}
                or type(record["version"]) is not int or record["version"] != 1
                or record["kind"] != kind or record["identifier"] != identifier
                or not isinstance(record["value"], str)):
            raise VaultError("Invalid bound personal mapping")
        return record["value"]

    def known_names(self) -> set[str]:
        """Reuse committed person mappings, without another plaintext index."""
        with self._vault.batch():
            names = set()
            for key in self._vault.name_keys():
                value = self.lookup('person_name', key.removeprefix('bound-person_name-'))
                if not value:
                    raise VaultError('Invalid committed person mapping')
                names.add(value)
            return names


def _key(kind: str, identifier: str) -> str:
    if (not isinstance(kind, str) or mode_for(kind) is not Mode.PSEUDONYMIZE
            or not isinstance(identifier, str) or not _IDENTIFIER.fullmatch(identifier)):
        raise VaultError("Invalid bound personal mapping identity")
    return f"bound-{kind}-{identifier}"
