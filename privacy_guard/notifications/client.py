"""Hook-side summary publisher; optional errors never affect protection."""

import os
import time
from pathlib import Path

from privacy_guard.notifications.config import read_mode
from privacy_guard.notifications.lifecycle import ensure_worker
from privacy_guard.notifications.queue import NotificationQueue
from privacy_guard.notifications.status import record_status


class NotificationJournal:
    def __init__(self, journal, directory, capture=None, launch=ensure_worker):
        self.journal, self.directory = journal, directory
        self.capture, self.launch = capture, launch
        self.session = None

    def __getattr__(self, attribute):
        return getattr(self.journal, attribute)

    def bind_context(self, event, session):
        self.session = session

    def record_protection(self, summary):
        self.journal.record_protection(summary)
        if read_mode(self.directory) == "off":
            return
        try:
            if self.capture is None:
                from privacy_guard.notifications.windows_origin import WindowsDesktop
                self.capture = WindowsDesktop().capture
            origin = self.capture()
        except Exception:
            origin = None
            record_status(self.directory, "origin_failed")
        try:
            NotificationQueue(self.directory).publish(self.session, origin, summary, time.time())
        except Exception:
            record_status(self.directory, "queue_failed")
            return
        try:
            self.launch(self.directory)
        except Exception:
            record_status(self.directory, "worker_failed")


def desktop_journal(journal, guard_home=None):
    directory = (guard_home or Path.home() / ".privacy-guard") / "notifications"
    if os.name != "nt" or read_mode(directory) == "off":
        return journal
    return NotificationJournal(journal, directory)
