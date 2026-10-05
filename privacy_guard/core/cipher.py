"""Encryption of the vault at rest (PRD §10), delegated to the operating system.

Python's standard library has no cipher, and a home-made one would be a
liability for a security product. Each platform adapter calls the OS's own,
audited protection instead:
- Windows: DPAPI (privacy_guard.core.dpapi)
- macOS: Keychain + CommonCrypto (not implemented yet)

Interface: `default_cipher() -> Cipher`, then `encrypt(bytes)` / `decrypt(bytes)`.
"""

from __future__ import annotations

import sys
from typing import Protocol


class Cipher(Protocol):
    """Encrypts and decrypts vault content."""

    def encrypt(self, data: bytes) -> bytes: ...

    def decrypt(self, data: bytes) -> bytes: ...


class UnsupportedPlatformError(RuntimeError):
    """No vault encryption is available on this platform yet."""


def default_cipher() -> Cipher:
    """Returns the cipher of the current platform, or raises if there is none."""
    if sys.platform == "win32":
        from privacy_guard.core.dpapi import DpapiCipher

        return DpapiCipher()
    raise UnsupportedPlatformError(f"Vault encryption is not available yet on {sys.platform}.")
