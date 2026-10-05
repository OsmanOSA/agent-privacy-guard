"""Synthetic values and test doubles shared by the test modules."""

from privacy_guard.core.name_detector import HeuristicNameDetector

# Assemble the synthetic key so source scanners do not flag a credential literal.
STRIPE_KEY = "sk_live_" + "FAKEFAKEFAKE00000000000000"


class RecordingNameService:
    """Stands in for the background service: finds names like the heuristic, records how it is used."""

    def __init__(self):
        self.started = False
        self.queried = []

    def ensure_running(self):
        self.started = True

    def find_names(self, text):
        self.queried.append(text)
        return HeuristicNameDetector().find_names(text)


class ReversingCipher:
    """Test cipher: reversible, fast, and visibly different from the plaintext."""

    PREFIX = b"enc:"

    def encrypt(self, data):
        return self.PREFIX + data[::-1]

    def decrypt(self, data):
        if not data.startswith(self.PREFIX):
            raise ValueError("Not encrypted by this cipher")
        return data[len(self.PREFIX):][::-1]
