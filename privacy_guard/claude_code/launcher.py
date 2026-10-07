"""Entry point of the installed hook.

The installer copies this file to ~/.privacy-guard/app/__main__.py, next to the
privacy_guard package. Claude Code then runs `python ~/.privacy-guard/app`, and
Python executes this file with app/ on its import path.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_BLOCK = 2
CORRUPTED_MESSAGE = (
    "Privacy Guard: installation is corrupted, action blocked. "
    "Reinstall or uninstall Privacy Guard from a terminal."
)


def main() -> int:
    # Claude Code exchanges UTF-8; the Windows default encoding (cp1252)
    # would fail on non-Latin content.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")

    try:
        from privacy_guard.claude_code.hook import run
        from privacy_guard.core.cipher import default_cipher
        from privacy_guard.core.vault import DEFAULT_VAULT_ROOT, VaultStore
        from privacy_guard.journal import EventJournal
        from privacy_guard.service.channel import DEFAULT_RUN_DIR, ServiceChannel
        from privacy_guard.service.client import ServiceClient

        vaults = VaultStore(DEFAULT_VAULT_ROOT, default_cipher())
        names = ServiceClient(ServiceChannel(DEFAULT_RUN_DIR))
    except Exception:
        return _unavailable()

    journal = EventJournal()
    try:
        from privacy_guard.notifications.client import desktop_journal
        journal = desktop_journal(journal)
    except Exception:
        pass  # Optional notifications cannot turn a working guard into a stop.
    return run(sys.stdin, sys.stdout, sys.stderr, journal, vaults, names)


def _unavailable() -> int:
    """Use only stdlib: the package itself may be missing or corrupted."""
    try:
        payload = json.loads(sys.stdin.read())
        event = payload.get("hook_event_name") if isinstance(payload, dict) else None
    except (ValueError, OSError):
        event = None
    try:
        path = Path.home() / '.privacy-guard/logs/failures.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        row = dict(timestamp=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                   event=event if isinstance(event, str) and event in {
                       'PreToolUse', 'PostToolUse', 'PostToolUseFailure', 'SessionStart', 'SessionEnd'} else 'unknown',
                   tool='unknown', stage='launcher_init', category='installation_unavailable')
        with path.open('a', encoding='utf-8') as journal:
            journal.write(json.dumps(row) + '\n')
    except Exception:
        pass  # Corrupt package and inaccessible logs must retain the stop response.
    if isinstance(event, str) and event in {"PostToolUse", "PostToolUseFailure"}:
        message = "Privacy Guard : installation indisponible, traitement interrompu. Réparez-la avant de reprendre."
        print(json.dumps({"continue": False, "stopReason": message, "systemMessage": message}, ensure_ascii=False))
        return 0
    if event == "PreToolUse":
        # A JSON deny keeps the hook command, and the user name in its paths, out of
        # model context (responses.deny).
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": CORRUPTED_MESSAGE}}))
        return 0
    print(CORRUPTED_MESSAGE, file=sys.stderr)
    return EXIT_BLOCK


if __name__ == "__main__":
    sys.exit(main())
