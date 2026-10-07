"""Place a card on its host monitor and return only to a verified host window."""

import ctypes as c
from ctypes import wintypes as w

from privacy_guard.notifications.windows_origin import WindowsDesktop, bind


class MonitorInfo(c.Structure):
    _fields_ = [("size", w.DWORD), ("monitor", w.RECT), ("work", w.RECT), ("flags", w.DWORD)]


def corner(work, width, height, margin=12):
    left, top, right, bottom = work
    return max(left, right - width - margin), max(top, bottom - height - margin)


class WindowsInteraction(WindowsDesktop):
    def __init__(self):
        super().__init__()
        bind(self.user, "MonitorFromWindow", w.HANDLE, [w.HWND, w.DWORD])
        bind(self.user, "GetMonitorInfoW", w.BOOL, [w.HANDLE, c.POINTER(MonitorInfo)])
        bind(self.user, "GetWindowRect", w.BOOL, [w.HWND, c.POINTER(w.RECT)])
        bind(self.user, "SetWindowPos", w.BOOL,
             [w.HWND, w.HWND, c.c_int, c.c_int, c.c_int, c.c_int, w.UINT])
        bind(self.user, "SetThreadDpiAwarenessContext", c.c_void_p, [c.c_void_p])
        bind(self.user, "IsIconic", w.BOOL, [w.HWND])
        bind(self.user, "ShowWindowAsync", w.BOOL, [w.HWND, c.c_int])
        bind(self.user, "SetForegroundWindow", w.BOOL, [w.HWND])

    def valid_origin(self, origin):
        return bool(origin and self.owner(origin["hwnd"]) == (origin["pid"], origin["created"]))

    def place(self, hwnd, origin):
        # Match physical screen coordinates across monitors with different scaling.
        old = self.user.SetThreadDpiAwarenessContext(c.c_void_p(-4))
        try:
            target = origin["hwnd"] if self.valid_origin(origin) else self.foreground()
            monitor = self.user.MonitorFromWindow(target, 2)
            info, rect = MonitorInfo(), w.RECT()
            info.size = c.sizeof(info)
            if not self.user.GetMonitorInfoW(monitor, c.byref(info)) or not self.user.GetWindowRect(hwnd, c.byref(rect)):
                raise OSError("Monitor geometry unavailable")
            if rect.right - rect.left < 100 or rect.bottom - rect.top < 100:
                raise OSError("Card dimensions are not usable")
            work = info.work
            x, y = corner((work.left, work.top, work.right, work.bottom), rect.right - rect.left,
                          rect.bottom - rect.top)
            # The hidden child is waiting for our display grant. A synchronous
            # cross-thread move would deadlock until the acknowledgement timeout.
            if not self.user.SetWindowPos(hwnd, None, x, y, 0, 0, 0x4015):
                raise OSError("Card placement unavailable")
        finally:
            if old:
                self.user.SetThreadDpiAwarenessContext(old)

    def activate(self, origin):
        if not self.valid_origin(origin):
            return False
        hwnd = origin["hwnd"]
        if self.user.IsIconic(hwnd):
            self.user.ShowWindowAsync(hwnd, 9)
        return bool(self.user.SetForegroundWindow(hwnd))
