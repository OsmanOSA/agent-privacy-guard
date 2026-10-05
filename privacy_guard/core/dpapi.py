"""Windows DPAPI cipher, called through ctypes.

DPAPI encrypts with a key derived from the Windows user's credentials: other
accounts, and anyone holding a copy of the disk without the user's password,
cannot decrypt. Processes running as the same user can: that is outside the
threat model (PRD §21).
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

# Extra secret mixed into the key: another application of the same user calling
# DPAPI without it cannot decrypt the vault.
APPLICATION_ENTROPY = b"agent-privacy-guard/vault/v1"
# Never show a Windows dialog: the hook runs headless.
CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _Blob(ctypes.Structure):
    """DATA_BLOB, the byte buffer structure DPAPI reads and writes."""

    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_char))]


class DpapiCipher:
    """Encrypts and decrypts bytes for the current Windows user."""

    def __init__(self) -> None:
        self._crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._declare_signatures()

    def encrypt(self, data: bytes) -> bytes:
        return self._transform(self._crypt32.CryptProtectData, data)

    def decrypt(self, data: bytes) -> bytes:
        """Raises OSError if the data was not encrypted by this user and application."""
        return self._transform(self._crypt32.CryptUnprotectData, data)

    def _transform(self, function,
                   data: bytes) -> bytes:
        # The buffers must stay referenced until the call returns, or ctypes may free them.
        source, _source_buffer = _blob(data)
        entropy, _entropy_buffer = _blob(APPLICATION_ENTROPY)
        result = _Blob()

        succeeded = function(
            ctypes.byref(source), None, ctypes.byref(entropy), None, None,
            CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(result),
        )
        if not succeeded:
            raise ctypes.WinError(ctypes.get_last_error())

        try:
            return ctypes.string_at(result.data, result.size)
        finally:
            # DPAPI allocates the output; we must release it.
            self._kernel32.LocalFree(ctypes.cast(result.data, ctypes.c_void_p))

    def _declare_signatures(self) -> None:
        # Explicit signatures: without them ctypes guesses, and a wrong guess corrupts memory.
        blob_pointer = ctypes.POINTER(_Blob)
        for function in (self._crypt32.CryptProtectData, self._crypt32.CryptUnprotectData):
            function.argtypes = [
                blob_pointer, ctypes.c_void_p, blob_pointer, ctypes.c_void_p,
                ctypes.c_void_p, wintypes.DWORD, blob_pointer,
            ]
            function.restype = wintypes.BOOL
        self._kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        self._kernel32.LocalFree.restype = ctypes.c_void_p


def _blob(data: bytes) -> tuple[_Blob, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data, len(data))
    return _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer
