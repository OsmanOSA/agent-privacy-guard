"""Best-effort fixed delivery codes, without bodies, exceptions or host IDs."""

import json
from datetime import datetime, timezone

CODES = {"accepted", "displayed", "hidden", "timed_out", "clicked", "transport_failed",
         "suppress_foreground", "send_unknown", "queue_failed", "origin_failed", "worker_failed",
         "card_rendered", "card_failed", "native_fallback", "off", "suppress_quiet",
         "quiet_state_unknown", "returned_to_host", "return_unavailable"}


def record_status(directory, code):
    if code not in CODES:
        return
    try:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "delivery.jsonl"
        # Keep at most one prior MiB; notification troubleshooting is bounded.
        if path.exists() and path.stat().st_size >= 1024 * 1024:
            path.replace(directory / "delivery.previous.jsonl")
        row = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": code}
        with path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(row) + "\n")
    except Exception:
        pass
