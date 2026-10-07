"""Answer before Claude Code's hook timeout ends the process.

Claude Code kills a hook that reaches its registered timeout, discards its answer
and sends the original tool result to the model (boundary scenario hook-timeout,
Claude Code 2.1.292). Catching errors inside the handler cannot help: any stage may
stall (service start, inference, vault). A timer therefore writes the fail-closed
answer shortly before the timeout and ends the process. Whichever answer comes
first is the only one written.

Interface:
    gate = AnswerGate(write)                  write(result) emits one HookResult
    timer = gate.deadline(seconds, fallback)  fallback() -> HookResult, built at expiry
    gate.answer(result) -> bool               False when the deadline answered first
    gate.written -> HookResult | None         the answer actually written
    timer.cancel()
"""

from __future__ import annotations

import os
import threading
from typing import Callable

from privacy_guard.claude_code.registration import HOOK_TIMEOUT_SECONDS
from privacy_guard.claude_code.responses import HookResult

# Leaves time to write the answer and for interpreter shutdown before the kill.
ANSWER_DEADLINE_SECONDS = HOOK_TIMEOUT_SECONDS - 5


class AnswerGate:
    """Lets exactly one of the normal answer and the deadline answer through."""

    def __init__(self, write: Callable[[HookResult], None]) -> None:
        self._write = write
        self._lock = threading.Lock()
        self.written: HookResult | None = None

    def answer(self, result: HookResult) -> bool:
        with self._lock:
            if self.written is not None:
                return False
            self.written = result
            self._write(result)
            return True

    def deadline(self, seconds: float, fallback: Callable[[], HookResult]) -> threading.Timer:
        timer = threading.Timer(seconds, self._expire, args=(fallback,))
        timer.daemon = True
        timer.start()
        return timer

    def _expire(self, fallback: Callable[[], HookResult]) -> None:
        result = fallback()
        if self.answer(result):
            # The main thread may be blocked in I/O; only a hard exit ends it in time.
            os._exit(result.exit_code)
