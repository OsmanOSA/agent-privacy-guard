"""Windows process ancestry and visible window handles, never titles or argv.

Capture requires a single visible window on a recognized ancestor. Unrelated
Windows Terminal server processes and multiple editor windows stay unknown.
"""

import ctypes as c
import os
from ctypes import wintypes as w

from privacy_guard.notifications.policy import choose_origin


class ProcessEntry(c.Structure):
    _fields_ = [("size", w.DWORD), ("usage", w.DWORD), ("pid", w.DWORD),
                ("heap", c.c_size_t), ("module", w.DWORD), ("threads", w.DWORD),
                ("parent", w.DWORD), ("priority", w.LONG), ("flags", w.DWORD),
                ("executable", w.WCHAR * 260)]


def bind(library, name, result, arguments):
    function = getattr(library, name)
    function.restype, function.argtypes = result, arguments
    return function


class WindowsDesktop:
    def __init__(self):
        if os.name != "nt":
            raise OSError("Windows notifications require Windows")
        self.kernel = c.WinDLL("kernel32", use_last_error=True)
        self.user = c.WinDLL("user32", use_last_error=True)
        bind(self.kernel, "CloseHandle", w.BOOL, [w.HANDLE])
        bind(self.kernel, "CreateToolhelp32Snapshot", w.HANDLE, [w.DWORD, w.DWORD])
        for name in ("Process32FirstW", "Process32NextW"):
            bind(self.kernel, name, w.BOOL, [w.HANDLE, c.POINTER(ProcessEntry)])
        bind(self.kernel, "OpenProcess", w.HANDLE, [w.DWORD, w.BOOL, w.DWORD])
        bind(self.kernel, "GetProcessTimes", w.BOOL, [w.HANDLE] + [c.POINTER(w.FILETIME)] * 4)
        bind(self.user, "GetWindowThreadProcessId", w.DWORD, [w.HWND, c.POINTER(w.DWORD)])
        bind(self.user, "GetForegroundWindow", w.HWND, [])
        bind(self.user, "GetWindow", w.HWND, [w.HWND, w.UINT])
        bind(self.user, "IsWindowVisible", w.BOOL, [w.HWND])
        self.callback = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        bind(self.user, "EnumWindows", w.BOOL, [self.callback, w.LPARAM])

    def processes(self):
        snapshot = self.kernel.CreateToolhelp32Snapshot(2, 0)
        if snapshot == c.c_void_p(-1).value:
            raise c.WinError(c.get_last_error())
        result, entry = {}, ProcessEntry()
        entry.size = c.sizeof(entry)
        try:
            valid = self.kernel.Process32FirstW(snapshot, c.byref(entry))
            while valid:
                result[entry.pid] = (entry.parent, entry.executable)
                valid = self.kernel.Process32NextW(snapshot, c.byref(entry))
            return result
        finally:
            self.kernel.CloseHandle(snapshot)

    def windows(self):
        result = {}

        @self.callback
        def visit(hwnd, _):
            if self.user.IsWindowVisible(hwnd) and not self.user.GetWindow(hwnd, 4):
                pid = w.DWORD()
                self.user.GetWindowThreadProcessId(hwnd, c.byref(pid))
                result.setdefault(pid.value, []).append(int(hwnd))
            return True

        if not self.user.EnumWindows(visit, 0):
            raise c.WinError(c.get_last_error())
        return result

    def owner(self, hwnd):
        pid = w.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, c.byref(pid))
        process = self.kernel.OpenProcess(0x1000, False, pid.value) if pid.value else None
        if not process:
            return None
        times = [w.FILETIME() for _ in range(4)]
        try:
            if not self.kernel.GetProcessTimes(process, *(c.byref(time) for time in times)):
                return None
            created = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
            return pid.value, created
        finally:
            self.kernel.CloseHandle(process)

    def capture(self):
        candidate = choose_origin(os.getpid(), self.processes(), self.windows())
        if not candidate:
            return None
        pid, hwnd, host = candidate
        owner = self.owner(hwnd)
        if owner is None or owner[0] != pid:
            return None
        return dict(pid=pid, hwnd=hwnd, created=owner[1], host=host)

    def foreground(self):
        return int(self.user.GetForegroundWindow() or 0)
