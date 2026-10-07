"""The background service: answers name-detection requests with a detector loaded once.

The channel opens immediately and the detector loads in parallel: a request
that arrives during the load waits for it instead of failing.

Requests and answers are JSON (never pickle: the channel must not be able to
run code). Requests are served one at a time, which keeps the detector free of
concurrency concerns.

Request:  {"op": "find_names", "text": "..."}  |  {"op": "ping"}  |  {"op": "stop"}
Answer:   {"findings": [[kind, start, end], ...]}  |  {"ready": bool}  |  {"error": "..."}
"""

from __future__ import annotations

import json
import os
import threading
import time
from multiprocessing.connection import Client, Connection, Listener
from multiprocessing.context import AuthenticationError
from pathlib import Path
from typing import Callable

from privacy_guard.core.name_detector import NameDetector
from privacy_guard.service.cached_names import CachedNameDetector
from privacy_guard.service.channel import ServiceChannel
from privacy_guard.diagnostics import failure_details, stage


def serve(channel: ServiceChannel,
          load_detector: Callable[[], NameDetector],
          idle_seconds: float) -> None:
    """Answers requests until asked to stop or left idle for `idle_seconds`."""
    _clear_stale_socket(channel)
    detector = _BackgroundLoad(load_detector)
    watchdog = _IdleWatchdog(idle_seconds)
    with Listener(channel.address, channel.family, authkey=channel.authkey()) as listener:
        while True:
            try:
                connection = listener.accept()
            except AuthenticationError:
                continue  # a client without the key: ignore it
            with connection:
                try:
                    keep_running = _answer(connection, detector)
                except (EOFError, OSError, ValueError):
                    continue  # the client vanished (e.g. hook timeout) or sent garbage
            if not keep_running:
                return
            watchdog.touch()


def _answer(connection: Connection,
            detector: _BackgroundLoad) -> bool:
    """Serves one request. Returns False when the service must stop."""
    request = json.loads(connection.recv_bytes())
    operation = request.get("op")
    if operation == "stop":
        connection.send_bytes(b'{"stopped": true}')
        return False
    if operation == "ping":
        answer = {"ready": detector.ready}
    else:
        answer = _find_names(detector, request["text"])
    connection.send_bytes(json.dumps(answer).encode("utf-8"))
    return True


def _find_names(detector: _BackgroundLoad,
                text: str) -> dict:
    try:
        with stage('model_loading'):
            names = detector.get()
        with stage('model_inference'):
            findings = names.find_names(text)
        answer = {"findings": [[f.kind, f.start, f.end] for f in findings]}
        if getattr(names, "reduced", None):
            answer["reduced"] = names.reduced
        return answer
    except Exception as error:
        # One bad request must not bring the service down; the hook will fail closed.
        at, category = failure_details(error)
        return {"error": category, "stage": at}


class _BackgroundLoad:
    """Builds the detector in a thread, so the channel answers from the first second."""

    def __init__(self, load: Callable[[], NameDetector]) -> None:
        self._loaded = threading.Event()
        self._detector: NameDetector | None = None
        self._error: Exception | None = None
        threading.Thread(target=self._run, args=(load,), daemon=True).start()

    @property
    def ready(self) -> bool:
        return self._loaded.is_set()

    def get(self) -> NameDetector:
        """Waits for the load to finish, then returns the detector or raises its error."""
        self._loaded.wait()
        if self._error is not None:
            raise self._error
        return self._detector

    def _run(self, load: Callable[[], NameDetector]) -> None:
        try:
            self._detector = CachedNameDetector(load())
        except Exception as error:
            self._error = error
        finally:
            self._loaded.set()


class _IdleWatchdog:
    """Ends the process after a period without requests, to give the memory back."""

    def __init__(self, idle_seconds: float) -> None:
        self._idle_seconds = idle_seconds
        self._last_activity = time.monotonic()
        threading.Thread(target=self._watch, daemon=True).start()

    def touch(self) -> None:
        self._last_activity = time.monotonic()

    def _watch(self) -> None:
        while True:
            time.sleep(min(self._idle_seconds, 30))
            if time.monotonic() - self._last_activity > self._idle_seconds:
                # accept() blocks the main thread; leaving from here is the only way out.
                os._exit(0)


def _clear_stale_socket(channel: ServiceChannel) -> None:
    # A Unix socket file outlives a crashed service and would block the next start.
    # Remove it only if nothing answers on it.
    if channel.family != "AF_UNIX" or not Path(channel.address).exists():
        return
    try:
        Client(channel.address, channel.family, authkey=channel.authkey()).close()
    except (ConnectionRefusedError, FileNotFoundError):
        Path(channel.address).unlink(missing_ok=True)
