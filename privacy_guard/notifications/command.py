"""Explicit preference and synthetic desktop test, without hook installation."""

import json
import os
import time

from privacy_guard.notifications.config import configure, read_mode, read_style
from privacy_guard.notifications.lifecycle import stop_worker
from privacy_guard.notifications.queue import NotificationQueue
from privacy_guard.notifications.status import record_status
from privacy_guard.notifications.presentation import banner_text, card_content, example_batch
from privacy_guard.notifications.renderer import create_renderer
from privacy_guard.notifications.display_context import DisplayContext


def notification_command(args):
    directory = args.guard_home / "notifications"
    try:
        if args.notification_mode or args.notification_style:
            if os.name != "nt" and args.notification_mode != "off":
                raise OSError("Desktop notifications currently support Windows only")
            configure(directory, args.notification_mode or read_mode(directory), args.notification_style)
            if args.notification_mode == "off":
                stop_worker(directory)
                NotificationQueue(directory).clear(time.time())
        if args.notification_test:
            return test_banner(directory)
        deployed = (args.guard_home / "app/privacy_guard/notifications/client.py").is_file()
        print(json.dumps({"mode": read_mode(directory), "style": read_style(directory), "hook_deployed": deployed,
                          "platform": "windows" if os.name == "nt" else "unsupported"}))
        return 0
    except Exception:
        print("Privacy Guard: notification configuration failed.")
        return 1


def test_banner(directory):
    banner = None
    try:
        banner = create_renderer(directory)
        batch = example_batch()
        outcome = banner.show(banner_text(batch), details=card_content(batch),
                              context=DisplayContext(directory, preview=True))
        record_status(directory, outcome)
        if outcome != "accepted":
            print(json.dumps({"accepted": False, "reason": outcome}))
            return 0
        displayed = False
        card_rendered = False
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            for code in banner.pump():
                record_status(directory, code)
                displayed = displayed or code == "displayed"
                card_rendered = card_rendered or code == "card_rendered"
            time.sleep(0.1)
        renderer = getattr(banner, "last_renderer", banner.kind)
        print(json.dumps({"accepted": True, "renderer": renderer, "card_rendered": card_rendered,
                          "shell_reported_display": displayed}))
        return 0
    except Exception:
        record_status(directory, "transport_failed")
        print(json.dumps({"accepted": False, "shell_reported_display": False}))
        return 1
    finally:
        if banner:
            banner.close()
