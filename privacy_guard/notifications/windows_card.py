"""Informational dark card, with a native banner when custom rendering fails."""

from privacy_guard.notifications.card_process import CardProcess
from privacy_guard.notifications.display_context import DisplayContext
from privacy_guard.notifications.status import record_status


class WindowsCard:
    kind = "card"

    def __init__(self, directory):
        self.directory = directory
        self.process = None
        self.fallback = None
        self.last_renderer = "card"
        self.events = []
        self.context = None

    def show(self, text, details=None, context=None):
        self.close()
        self.context = context or DisplayContext(self.directory, preview=True)
        decision = self.context.decision()
        if decision not in {"card", "native"}:
            self.events.append(decision)
            return decision
        if decision == "native":
            return self._native(text)
        self.process = CardProcess()
        try:
            outcome = self.process.start(details or {
                "headline": "Protection appliquée", "document": "Résultat d’outil",
                "details": text, "footer": "Traitement local"}, self.context)
        except Exception:
            outcome = "failed"
        if outcome == "rendered":
            self.last_renderer = "card"
            self.events.append("card_rendered")
            return "accepted"
        self.process.stop()
        self.process = None
        if outcome in {"off", "suppress_foreground", "suppress_quiet"}:
            self.events.append(outcome)
            return outcome
        if outcome == "failed":
            record_status(self.directory, "card_failed")
        return self._native(text)

    def _native(self, text):
        from privacy_guard.notifications.windows_banner import WindowsBanner
        self.fallback = WindowsBanner()
        self.last_renderer = "native"
        record_status(self.directory, "native_fallback")
        return self.fallback.show(text, context=self.context)

    def pump(self):
        if self.process:
            for event in self.process.pump():
                if event == "clicked":
                    self.events.append("returned_to_host" if self.context.activate() else "return_unavailable")
            if self.process.process and self.process.process.poll() is None:
                decision = self.context.decision()
                if decision != "card":
                    self.process.stop()
                    self.events.append(decision if decision != "native" else "quiet_state_unknown")
        events, self.events = self.events, []
        return events + (self.fallback.pump() if self.fallback else [])

    def close(self):
        try:
            if self.process:
                self.process.stop()
        finally:
            self.process = None
            if self.fallback:
                self.fallback.close()
                self.fallback = None
