"""Exclusive native handles for validating and updating an already-written file.

Interface: existing_file(path), read(handle, limit), replace(handle, bytes).
Reuse directory pinning from WindowsFiles. Reject non-disk files, directories,
reparse points and multiple hard links before any restoration or replacement.
"""

from __future__ import annotations

import ctypes
from contextlib import contextmanager
from ctypes import wintypes
from pathlib import Path

from privacy_guard.exports.windows_files import WindowsFiles, _require

_READ_WRITE_DELETE = 0xC0010000
_OPEN_EXISTING = 3
_OPEN_REPARSE_POINT = 0x00200000
_UNSAFE_ATTRIBUTES = 0x410  # FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT.


class _FileInfo(ctypes.Structure):
    _fields_ = [("attributes", wintypes.DWORD), ("created", wintypes.FILETIME),
                ("accessed", wintypes.FILETIME), ("written", wintypes.FILETIME),
                ("volume", wintypes.DWORD), ("size_high", wintypes.DWORD),
                ("size_low", wintypes.DWORD), ("links", wintypes.DWORD),
                ("index_high", wintypes.DWORD), ("index_low", wintypes.DWORD)]


class WrittenFileHandles(WindowsFiles):
    """Read and replace through one exclusively held file object, never a reopened path."""

    def __init__(self) -> None:
        super().__init__()
        signatures = {
            "GetFileInformationByHandle": ([wintypes.HANDLE, ctypes.POINTER(_FileInfo)], wintypes.BOOL),
            "GetFileType": ([wintypes.HANDLE], wintypes.DWORD),
            "ReadFile": ([wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                          ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p], wintypes.BOOL),
            "SetFilePointerEx": ([wintypes.HANDLE, ctypes.c_longlong, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            "SetEndOfFile": ([wintypes.HANDLE], wintypes.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self._api, name)
            function.argtypes, function.restype = arguments, result

    @contextmanager
    def existing_file(self, path: Path):
        handle = self._open(path, _READ_WRITE_DELETE, 0, _OPEN_EXISTING, _OPEN_REPARSE_POINT)
        try:
            self.validate(handle)
            yield handle
        finally:
            _require(self._api.CloseHandle(handle))

    def validate(self, handle) -> None:
        info = _FileInfo()
        _require(self._api.GetFileInformationByHandle(handle, ctypes.byref(info)))
        if self._api.GetFileType(handle) != 1 or info.attributes & _UNSAFE_ATTRIBUTES or info.links != 1:
            raise OSError("Local restoration requires a plain file with one link")

    def read(self, handle, limit: int) -> bytes:
        chunks, total = [], 0
        while True:
            buffer = ctypes.create_string_buffer(65536)
            count = wintypes.DWORD()
            _require(self._api.ReadFile(handle, buffer, len(buffer), ctypes.byref(count), None))
            if not count.value:
                return b"".join(chunks)
            total += count.value
            if total > limit:
                raise ValueError("Local restoration file is too large")
            chunks.append(buffer.raw[:count.value])

    def replace(self, handle, data: bytes) -> None:
        """Replace bytes on this object and truncate the old tail, retaining exclusive access."""
        _require(self._api.SetFilePointerEx(handle, 0, None, 0))
        self.write(handle, data)
        _require(self._api.SetEndOfFile(handle))
        _require(self._api.FlushFileBuffers(handle))
