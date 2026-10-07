"""Prepare WPF hidden, recheck policy, then grant display through bounded IPC."""

import json
import os
import queue
import subprocess
import threading
from pathlib import Path

from privacy_guard.notifications.card_script import CLICKED, PREPARED, READY, encoded_script


def powershell():
    return str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe")


class CardProcess:
    def __init__(self):
        self.process = None
        self.events = queue.SimpleQueue()
        self.reader = None

    def start(self, content, context, timeout=5):
        limits = {"headline": 64, "document": 120, "details": 2048, "footer": 64}
        if any(not isinstance(content.get(key), str) or len(content[key]) > limit for key, limit in limits.items()):
            raise ValueError("Invalid card summary")
        self.process = subprocess.Popen(
            [powershell(), "-NoLogo", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
             "-STA", "-EncodedCommand", encoded_script()],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)
        process, completed, result = self.process, threading.Event(), []

        def acknowledge():
            hwnd = None
            try:
                for _ in range(8):
                    line = process.stdout.readline(512).decode("ascii").strip()
                    if not line:
                        break
                    if line.startswith(PREPARED) and hwnd is None:
                        hwnd = int(line[len(PREPARED):])
                        decision = context.decision()
                        if decision == "card":
                            context.place(hwnd)
                            decision = context.decision()
                        allowed = decision == "card"
                        process.stdin.write(json.dumps({"show": allowed, "can_return": bool(context.origin)}).encode() + b"\n")
                        process.stdin.flush()
                        process.stdin.close()
                        if not allowed:
                            result.append(decision)
                            break
                    elif line == READY and hwnd is not None:
                        context.place(hwnd)
                        result.append("rendered")
                        completed.set()
                    elif line == CLICKED and result == ["rendered"]:
                        self.events.put("clicked")
            except Exception:
                pass
            finally:
                completed.set()

        self.reader = threading.Thread(target=acknowledge, daemon=True, name="card-acknowledgement")
        self.reader.start()
        try:
            payload = {key: content[key] for key in limits}
            payload["return_pid"] = os.getpid()
            process.stdin.write(json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n")
            process.stdin.flush()
            completed.wait(timeout)
            return result[0] if result else "failed"
        except Exception:
            self.stop()
            raise

    def pump(self):
        events = []
        while not self.events.empty():
            events.append(self.events.get_nowait())
        return events

    def stop(self):
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=1)
            if self.reader:
                self.reader.join(timeout=1)
            for stream in (self.process.stdin, self.process.stdout):
                stream.close()
            self.process = None
