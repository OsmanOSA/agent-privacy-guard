"""Entry point of the installed hook.

The installer copies this file to ~/.privacy-guard/app/__main__.py, next to the
privacy_guard package. Claude Code then runs `python ~/.privacy-guard/app`, and
Python executes this file with app/ on its import path.
"""

import sys

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
        # Fail closed: without the engine or its encryption, block rather than let content through.
        print(CORRUPTED_MESSAGE, file=sys.stderr)
        return EXIT_BLOCK

    return run(sys.stdin, sys.stdout, sys.stderr, EventJournal(), vaults, names)


if __name__ == "__main__":
    sys.exit(main())
