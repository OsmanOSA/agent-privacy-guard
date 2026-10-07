"""Grouped delivery off the hook path. At most one banner per eight seconds."""

import time

from privacy_guard.notifications.config import read_mode, read_style
from privacy_guard.notifications.lifecycle import WorkerLease
from privacy_guard.notifications.policy import delivery_policy
from privacy_guard.notifications.queue import NotificationQueue
from privacy_guard.notifications.status import record_status
from privacy_guard.notifications.presentation import banner_text, card_content
from privacy_guard.notifications.renderer import create_renderer
from privacy_guard.notifications.display_context import DisplayContext


def deliver(batch, mode, desktop, banner, directory):
    origin = batch["origin"]
    try:
        foreground = desktop.foreground()
        owner = desktop.owner(origin["hwnd"]) if origin else None
        decision = delivery_policy(mode, origin, foreground, owner)
    except Exception:
        decision = "off" if mode == "off" else "send_unknown"
    if decision in {"off", "suppress_foreground"}:
        record_status(directory, decision)
        return decision
    if decision == "send_unknown":
        record_status(directory, decision)
    try:
        context = DisplayContext(directory, origin, mode)
        outcome = banner.show(banner_text(batch), details=card_content(batch), context=context)
        outcome = outcome if isinstance(outcome, str) else "accepted"
        record_status(directory, outcome)
        return outcome
    except Exception:
        record_status(directory, "transport_failed")
        return "transport_failed"


def run_worker(directory):
    from privacy_guard.notifications.windows_origin import WindowsDesktop

    lease = WorkerLease(directory)
    if not lease.handle:
        (directory / "launch.claim").unlink(missing_ok=True)
        return 0
    heartbeat, banner = directory / "worker.live", None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        heartbeat.touch()
        (directory / "launch.claim").unlink(missing_ok=True)
        desktop, queue = WindowsDesktop(), NotificationQueue(directory)
        deadline, next_banner = time.monotonic() + 60, 0
        while time.monotonic() < deadline and not (directory / "stop").exists():
            mode = read_mode(directory)
            if mode == "off":
                break
            if banner and banner.kind != read_style(directory):
                banner.close()
                banner = None
            heartbeat.touch()
            if banner:
                for code in banner.pump():
                    record_status(directory, code)
            if time.monotonic() >= next_banner:
                batches = queue.take_due(time.time(), limit=1)
                for batch in batches:
                    if banner is None:
                        try:
                            banner = create_renderer(directory)
                        except Exception:
                            record_status(directory, "transport_failed")
                            continue
                    deliver(batch, mode, desktop, banner, directory)
                    next_banner = time.monotonic() + 8
                    deadline = time.monotonic() + 60
            time.sleep(0.2)
        return 0
    except Exception:
        record_status(directory, "worker_failed")
        return 1
    finally:
        try:
            if banner:
                banner.close()
        except Exception:
            record_status(directory, "transport_failed")
        finally:
            heartbeat.unlink(missing_ok=True)
            lease.close()
