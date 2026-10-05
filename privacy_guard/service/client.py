"""The hook's side of the background service: ask, and start the service if needed.

Interface:
    client = ServiceClient(channel)
    client.ensure_running()                    (starts the service without waiting: session start)
    client.is_ready() -> bool                  (running with its detector loaded)
    client.find_names(text) -> list[Finding]   (starts the service and waits if needed)
    client.stop() -> bool                      (True if a running service was stopped)
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from multiprocessing.connection import Client, Connection
from pathlib import Path

import privacy_guard
from privacy_guard.core.findings import Finding
from privacy_guard.service.channel import ServiceChannel
from privacy_guard.service.model_environment import ModelEnvironment

# The directory that contains the privacy_guard package: `python -m` must run from there.
APP_ROOT = Path(privacy_guard.__file__).resolve().parent.parent
# The model environment, when installed: its Python can run the NER model.
MODEL_PYTHON = ModelEnvironment().python

CONNECT_TIMEOUT_SECONDS = 8.0
# Long enough to wait for the model to load once (~10 s), below the hook timeout
# (30 s): a slow answer fails closed instead of the hook being killed.
ANSWER_TIMEOUT_SECONDS = 25.0
RETRY_DELAY_SECONDS = 0.05


class ServiceError(RuntimeError):
    """The service could not answer; the hook must fail closed."""


class ServiceClient:
    """Queries the background service, starting it when it is not running."""

    def __init__(self, channel: ServiceChannel,
                 python: Path | None = None) -> None:
        self._channel = channel
        self._python = python or (MODEL_PYTHON if MODEL_PYTHON.exists() else Path(sys.executable))

    def ensure_running(self) -> None:
        connection = self._connect()
        if connection is None:
            self._launch()
        else:
            connection.close()

    def find_names(self, text: str) -> list[Finding]:
        answer = self._request({"op": "find_names", "text": text})
        if "error" in answer:
            raise ServiceError(answer["error"])
        return [Finding(kind, start, end) for kind, start, end in answer["findings"]]

    def is_ready(self) -> bool:
        """True once the service runs and its detector is loaded. Never starts the service."""
        connection = self._connect()
        if connection is None:
            return False
        with connection:
            connection.send_bytes(b'{"op": "ping"}')
            return connection.poll(ANSWER_TIMEOUT_SECONDS) and json.loads(connection.recv_bytes())["ready"]

    def stop(self) -> bool:
        connection = self._connect()
        if connection is None:
            return False
        with connection:
            connection.send_bytes(b'{"op": "stop"}')
            connection.recv_bytes()
        return True

    def _request(self, request: dict) -> dict:
        with self._connect() or self._start_and_connect() as connection:
            connection.send_bytes(json.dumps(request).encode("utf-8"))
            if not connection.poll(ANSWER_TIMEOUT_SECONDS):
                raise ServiceError("The background service did not answer in time")
            return json.loads(connection.recv_bytes())

    def _connect(self) -> Connection | None:
        try:
            return Client(self._channel.address, self._channel.family, authkey=self._channel.authkey())
        except (FileNotFoundError, ConnectionRefusedError):
            return None  # not running (yet)

    def _start_and_connect(self) -> Connection:
        self._launch()
        deadline = time.monotonic() + CONNECT_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            connection = self._connect()
            if connection is not None:
                return connection
            time.sleep(RETRY_DELAY_SECONDS)
        raise ServiceError("The background service did not start in time")

    def _launch(self) -> None:
        # Fully detached, with no inherited stdout/stderr: Claude Code waits for the
        # hook's output pipes to close, and the service must not hold them open.
        command = [str(self._python), "-m", "privacy_guard.service", "--run-dir", str(self._channel.run_dir)]
        options = {"cwd": APP_ROOT, "stdin": subprocess.DEVNULL,
                   "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if sys.platform == "win32":
            options["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            options["start_new_session"] = True
        subprocess.Popen(command, **options)
