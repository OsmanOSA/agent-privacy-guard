"""Recheck optional notification policy at presentation and during card lifetime."""

from privacy_guard.notifications.config import read_mode
from privacy_guard.notifications.policy import delivery_policy
from privacy_guard.notifications.windows_attention import notification_state


class DisplayContext:
    def __init__(self, directory, origin=None, mode="always", desktop=None, attention=notification_state,
                 preview=False):
        self.directory, self.origin, self.mode = directory, origin, mode
        if desktop is None:
            from privacy_guard.notifications.windows_interaction import WindowsInteraction
            desktop = WindowsInteraction()
        self.desktop, self.attention, self.preview = desktop, attention, preview

    def decision(self):
        mode = self.mode if self.preview else read_mode(self.directory)
        if mode == "off":
            return "off"
        try:
            owner = self.desktop.owner(self.origin["hwnd"]) if self.origin else None
            decision = delivery_policy(mode, self.origin, self.desktop.foreground(), owner)
            if decision == "suppress_foreground":
                return decision
            state = self.attention()
            if state == "quiet":
                return "suppress_quiet"
            return "card" if state == "available" else "native"
        except Exception:
            return "native"

    def place(self, hwnd):
        self.desktop.place(hwnd, self.origin)

    def activate(self):
        try:
            return self.desktop.activate(self.origin)
        except Exception:
            return False
