"""One detached worker per notification directory, using a Windows mutex."""

import ctypes as c
import hashlib
import os
import subprocess
import sys
import threading
import time
from ctypes import wintypes as w
from pathlib import Path

HEARTBEAT_TTL = 8  # Custom-card startup acknowledgement can take five seconds.


class WorkerLease:
    def __init__(self, directory):
        kernel = c.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.argtypes = [c.c_void_p, w.BOOL, w.LPCWSTR]
        kernel.CreateMutexW.restype = w.HANDLE
        kernel.CloseHandle.argtypes, kernel.CloseHandle.restype = [w.HANDLE], w.BOOL
        kernel.ReleaseMutex.argtypes, kernel.ReleaseMutex.restype = [w.HANDLE], w.BOOL
        identity = hashlib.sha256(str(directory.resolve()).encode()).hexdigest()
        c.set_last_error(0)
        self.handle = kernel.CreateMutexW(None, True, "Local\\PrivacyGuardNotifications-" + identity)
        self.kernel = kernel
        if not self.handle:
            raise c.WinError(c.get_last_error())
        if c.get_last_error() == 183:
            kernel.CloseHandle(self.handle)
            self.handle = None

    def close(self):
        if self.handle:
            self.kernel.ReleaseMutex(self.handle)
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def ensure_worker(directory: Path):
    if (directory / "stop").exists():
        return
    heartbeat = directory / "worker.live"
    try:
        age = time.time() - heartbeat.stat().st_mtime
        if 0 <= age <= HEARTBEAT_TTL:
            return
    except FileNotFoundError:
        pass
    # O_EXCL prevents a burst of subprocesses before the worker starts.
    claim = directory / "launch.claim"
    try:
        with claim.open("x", encoding="ascii"):
            pass
    except FileExistsError:
        try:
            if 0 <= time.time() - claim.stat().st_mtime <= 5:
                return
            claim.unlink(missing_ok=True)
            with claim.open("x", encoding="ascii"):
                pass
        except (FileNotFoundError, FileExistsError):
            return  # Another publisher or the worker completed the handshake.
    package_root = str(Path(__file__).resolve().parents[2])
    environment = dict(os.environ, PYTHONPATH=package_root)
    try:
        process = subprocess.Popen([sys.executable, "-m", "privacy_guard.notifications", "worker",
                          "--directory", str(directory.resolve())], env=environment,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                         close_fds=True)
        # Retain/reap the child during long-lived CLI calls; a hook never waits.
        threading.Thread(target=process.wait, daemon=True, name="notification-reaper").start()
    except Exception:
        claim.unlink(missing_ok=True)
        raise


def stop_worker(directory: Path):
    if not directory.exists():
        return
    stop = directory / "stop"
    stop.write_text("stop", encoding="ascii")
    deadline = time.monotonic() + 10
    while True:
        pending = False
        for name, ttl in (("worker.live", HEARTBEAT_TTL), ("launch.claim", 5)):
            try:
                age = time.time() - (directory / name).stat().st_mtime
                pending = pending or 0 <= age <= ttl
            except FileNotFoundError:
                pass
        if not pending:
            break
        if time.monotonic() >= deadline:
            # Keep the stop request; do not let a late old worker outlive upgrade.
            raise TimeoutError("Notification worker did not stop")
        time.sleep(0.05)
    stop.unlink(missing_ok=True)
