"""Native notification-area banners via Shell_NotifyIconW, stdlib only.

Own hidden message window and temporary tray icon; no focus change, startup
registration or executable launched on click. Windows controls visual delivery.
Windows 11 banners are transient, unlike persisted modern app toasts.
"""

import ctypes as c
from ctypes import wintypes as w

from privacy_guard.notifications.windows_origin import WindowsDesktop, bind

CALLBACK = 0x8001
SHELL_EVENTS = {0x402: "displayed", 0x403: "hidden", 0x404: "timed_out", 0x405: "clicked"}


class IconData(c.Structure):
    _fields_ = [("cbSize", w.DWORD), ("hWnd", w.HWND), ("uID", w.UINT),
                ("uFlags", w.UINT), ("uCallbackMessage", w.UINT), ("hIcon", w.HICON),
                ("szTip", w.WCHAR * 128), ("dwState", w.DWORD), ("dwStateMask", w.DWORD),
                ("szInfo", w.WCHAR * 256), ("uVersion", w.UINT),
                ("szInfoTitle", w.WCHAR * 64), ("dwInfoFlags", w.DWORD),
                ("guidItem", c.c_byte * 16), ("hBalloonIcon", w.HICON)]


class WindowsBanner:
    kind = "native"

    def __init__(self):
        desktop = WindowsDesktop()
        self.user = desktop.user
        self.shell = c.WinDLL("shell32", use_last_error=True)
        bind(self.shell, "Shell_NotifyIconW", w.BOOL, [w.DWORD, c.POINTER(IconData)])
        bind(self.user, "CreateWindowExW", w.HWND,
             [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, c.c_int, c.c_int, c.c_int, c.c_int,
              w.HWND, w.HMENU, w.HINSTANCE, c.c_void_p])
        bind(self.user, "LoadIconW", w.HICON, [w.HINSTANCE, c.c_void_p])
        bind(self.user, "DestroyWindow", w.BOOL, [w.HWND])
        bind(self.user, "PeekMessageW", w.BOOL, [c.POINTER(w.MSG), w.HWND, w.UINT, w.UINT, w.UINT])
        bind(self.user, "TranslateMessage", w.BOOL, [c.POINTER(w.MSG)])
        bind(self.user, "DispatchMessageW", c.c_ssize_t, [c.POINTER(w.MSG)])
        self._events = []
        self._previous = None
        self._set_proc = bind(self.user, "SetWindowLongPtrW" if c.sizeof(c.c_void_p) == 8 else "SetWindowLongW",
                              c.c_void_p, [w.HWND, c.c_int, c.c_void_p])
        bind(self.user, "CallWindowProcW", c.c_ssize_t, [c.c_void_p, w.HWND, w.UINT, w.WPARAM, w.LPARAM])
        callback_type = c.WINFUNCTYPE(c.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
        self._window_proc = callback_type(self._callback)
        self.data = IconData()
        self.data.cbSize = c.sizeof(IconData)
        self.data.hWnd = self.user.CreateWindowExW(0, "STATIC", "Privacy Guard", 0,
                                                 0, 0, 0, 0, w.HWND(-3), None, None, None)
        if not self.data.hWnd:
            raise c.WinError(c.get_last_error())
        self._previous = self._set_proc(self.data.hWnd, -4, c.cast(self._window_proc, c.c_void_p))
        if not self._previous:
            self.close()
            raise OSError("Notification callback unavailable")
        self.data.uID, self.data.uFlags, self.data.uCallbackMessage = 1, 7, CALLBACK
        self.data.hIcon = self.user.LoadIconW(None, c.c_void_p(32516))
        self.data.szTip = "Privacy Guard"
        if not self.shell.Shell_NotifyIconW(0, c.byref(self.data)):
            self.close()
            raise OSError("Notification area unavailable")
        self.data.uVersion = 4
        if not self.shell.Shell_NotifyIconW(4, c.byref(self.data)):
            self.close()
            raise OSError("Notification icon version unavailable")

    def show(self, text, details=None, context=None):
        self.context = context
        if context:
            decision = context.decision()
            if decision not in {"card", "native"}:
                return decision
        self.data.uFlags = 0x10
        self.data.szInfoTitle = "Privacy Guard"
        # Native limits are UTF-16 code units, not Python character counts.
        self.data.szInfo = text.encode("utf-16-le")[:510].decode("utf-16-le", errors="ignore")
        self.data.dwInfoFlags = 1 | 0x80  # Informational; respect Windows quiet time.
        if not self.shell.Shell_NotifyIconW(1, c.byref(self.data)):
            raise OSError("Notification submission failed")
        return "accepted"

    def pump(self):
        message = w.MSG()
        while self.user.PeekMessageW(c.byref(message), None, 0, 0, 1):
            self.user.TranslateMessage(c.byref(message))
            self.user.DispatchMessageW(c.byref(message))
        result, self._events = self._events, []
        if "clicked" in result and getattr(self, "context", None):
            result.append("returned_to_host" if self.context.activate() else "return_unavailable")
        return result

    def _callback(self, hwnd, message, wparam, lparam):
        if message == CALLBACK:
            event = SHELL_EVENTS.get(lparam & 0xffff)
            if event:
                self._events.append(event)
            return 0
        return self.user.CallWindowProcW(self._previous, hwnd, message, wparam, lparam)

    def close(self):
        if self.data.hWnd:
            self.shell.Shell_NotifyIconW(2, c.byref(self.data))
            if self._previous:
                self._set_proc(self.data.hWnd, -4, self._previous)
            self.user.DestroyWindow(self.data.hWnd)
            self.data.hWnd = None
