"""Read-only Windows interruption state; unknown means use shell-managed delivery.

SHQueryUserNotificationState covers presentation/fullscreen/absence, not modern
Do Not Disturb. The WNF quiet profile is undocumented: strictly validate its
payload and fall back to native delivery if Windows changes the contract.
"""

import ctypes as c
from ctypes import wintypes as w

from privacy_guard.notifications.windows_origin import bind


def quiet_profile():
    library = c.WinDLL("ntdll")
    query = bind(library, "NtQueryWnfStateData", w.LONG,
                 [c.POINTER(c.c_ulonglong), c.c_void_p, c.c_void_p,
                  c.POINTER(w.ULONG), c.POINTER(w.DWORD), c.POINTER(w.ULONG)])
    name = c.c_ulonglong(0x0D83063EA3BF1C75)
    stamp, value, size = w.ULONG(), w.DWORD(), w.ULONG(4)
    status = query(c.byref(name), None, None, c.byref(stamp), c.byref(value), c.byref(size))
    if status != 0 or size.value != 4 or value.value not in (0, 1, 2):
        return None
    return value.value


def notification_state():
    try:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\PushNotifications") as key:
                enabled, _ = winreg.QueryValueEx(key, "ToastEnabled")
                if enabled == 0:
                    return "quiet"
        except FileNotFoundError:
            pass
        shell = c.WinDLL("shell32")
        query = bind(shell, "SHQueryUserNotificationState", w.LONG, [c.POINTER(c.c_int)])
        state = c.c_int()
        if query(c.byref(state)) != 0:
            return "unknown"
        if state.value in (1, 2, 3, 4, 6):
            return "quiet"
        if state.value not in (5, 7):
            return "unknown"
        profile = quiet_profile()
        return "unknown" if profile is None else ("quiet" if profile else "available")
    except (OSError, AttributeError, ValueError):
        return "unknown"
