"""Windows handles for pinned directories and exclusive new export files.

Interface: WindowsFiles().directory(path) / new_file(path), then write(handle, bytes).
Directory handles exclude delete sharing and reject reparse points. New files
are never opened for replacement. Exceptions contain an error code, not data.
"""

from __future__ import annotations

import ctypes
import sys
from contextlib import contextmanager
from ctypes import wintypes
from pathlib import Path

_DIRECTORY_READ = 0x81  # FILE_LIST_DIRECTORY counts as read access for sharing checks.
_DELETE = 0x10000
_GENERIC_WRITE = 0x40000000
_SHARE_READ_WRITE = 3
_OPEN_EXISTING = 3
_CREATE_NEW = 1
_BACKUP_SEMANTICS = 0x02000000
_OPEN_REPARSE_POINT = 0x00200000
_DIRECTORY = 0x10
_REPARSE_POINT = 0x400


class _Attributes(ctypes.Structure):
    _fields_ = [("attributes", wintypes.DWORD), ("tag", wintypes.DWORD)]


class WindowsFiles:
    """Own native handles; refuse unsupported platforms instead of using a weaker writer."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise OSError("The local export writer requires native Windows")
        self._api = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateFileW": ([wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                             wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE], wintypes.HANDLE),
            "GetFileInformationByHandleEx": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            "SetFileInformationByHandle": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            "WriteFile": ([wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p], wintypes.BOOL),
            "FlushFileBuffers": ([wintypes.HANDLE], wintypes.BOOL),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self._api, name)
            function.argtypes, function.restype = arguments, result

    @contextmanager
    def directory(self, path: Path):
        """Pin one real directory against rename/deletion until the context ends."""
        handle = self._open(path, _DIRECTORY_READ, _SHARE_READ_WRITE, _OPEN_EXISTING,
                            _BACKUP_SEMANTICS | _OPEN_REPARSE_POINT)
        try:
            info = _Attributes()
            _require(self._api.GetFileInformationByHandleEx(handle, 9, ctypes.byref(info), ctypes.sizeof(info)))
            if info.attributes & _REPARSE_POINT or not info.attributes & _DIRECTORY:
                raise OSError("Export directory is not a plain directory")
            yield handle
        finally:
            _require(self._api.CloseHandle(handle))

    @contextmanager
    def new_file(self, path: Path):
        """Create once, with exclusive sharing; discard by handle on a handled failure."""
        handle = self._open(path, _GENERIC_WRITE | _DELETE, 0, _CREATE_NEW, _OPEN_REPARSE_POINT)
        try:
            yield handle
        except BaseException:
            delete = ctypes.c_ubyte(1)
            _require(self._api.SetFileInformationByHandle(handle, 4, ctypes.byref(delete), ctypes.sizeof(delete)))
            raise
        finally:
            _require(self._api.CloseHandle(handle))

    def write(self, handle, data: bytes) -> None:
        """Write every byte to this handle and flush before releasing exclusive access."""
        offset = 0
        while offset < len(data):
            chunk = data[offset:offset + 65536]
            buffer = ctypes.create_string_buffer(chunk, len(chunk))
            written = wintypes.DWORD()
            _require(self._api.WriteFile(handle, buffer, len(chunk), ctypes.byref(written), None))
            if not written.value:
                raise OSError("Export write made no progress")
            offset += written.value
        _require(self._api.FlushFileBuffers(handle))

    def _open(self, path: Path, access: int, sharing: int, creation: int, flags: int):
        handle = self._api.CreateFileW(str(path), access, sharing, None, creation, flags, None)
        _require(handle is not None and handle != ctypes.c_void_p(-1).value)
        return handle


def _require(succeeded) -> None:
    if not succeeded:
        raise OSError(ctypes.get_last_error(), "Local export file operation failed")
