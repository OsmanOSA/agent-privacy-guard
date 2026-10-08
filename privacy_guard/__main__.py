"""Privacy Guard command line.

Usage, from the project root:
    python -m privacy_guard install [--model-source DIRECTORY_OR_HTTPS_URL]
    python -m privacy_guard status
    python -m privacy_guard uninstall
    python -m privacy_guard export --source masked.csv --session ID --filename clients.csv
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from privacy_guard.claude_code.installer import ClaudeCodeInstaller, ClaudeCodeNotFoundError
from privacy_guard.claude_code.vault_format import VaultCompatibilityError
from privacy_guard.core.cipher import UnsupportedPlatformError
from privacy_guard.exports.command import export_csv
from privacy_guard.service.name_model_setup import DEFAULT_MODEL_SOURCE, NameModelSetup, NameModelSetupError


@dataclass(frozen=True)
class Installers:
    """Everything the command line drives: the Claude Code hook and the optional name model."""

    claude_code: ClaudeCodeInstaller
    name_model: NameModelSetup


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = _parse_args(argv)
    if args.action == "notifications":
        from privacy_guard.notifications.command import notification_command
        return notification_command(args)
    if args.action == "export":
        return export_csv(args.source, args.session, args.filename, args.guard_home)
    installers = Installers(
        ClaudeCodeInstaller(args.claude_dir, args.guard_home, Path(sys.executable)),
        NameModelSetup(args.guard_home),
    )
    actions = {"install": _install, "uninstall": _uninstall, "status": _status}
    return actions[args.action](installers, args)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="privacy_guard", description="Privacy Guard for Claude Code")
    parser.add_argument("action", nargs="?", default="status", choices=["install", "uninstall", "status", "export", "notifications"])
    parser.add_argument("--claude-dir", type=Path, default=Path.home() / ".claude")
    parser.add_argument("--guard-home", type=Path, default=Path.home() / ".privacy-guard")
    parser.add_argument("--model-source", default=DEFAULT_MODEL_SOURCE,
                        help="directory or https:// URL holding the converted name model")
    parser.add_argument("--source", type=Path, help="masked CSV or SQL file to export")
    parser.add_argument("--session", help="session that issued the CSV tokens")
    parser.add_argument("--filename", help="unused CSV or SQL filename inside the configured export root")
    parser.add_argument("--notification-mode", choices=["off", "background", "always"])
    parser.add_argument("--notification-style", choices=["card", "native"])
    parser.add_argument("--notification-test", action="store_true", help="send one synthetic Windows banner")
    args = parser.parse_args(argv)
    if args.action == "export" and any(value is None for value in (args.source, args.session, args.filename)):
        parser.error("export requires --source, --session and --filename")
    if args.action != "notifications" and (args.notification_mode or args.notification_style or args.notification_test):
        parser.error("notification options require the notifications action")
    return args


def _install(installers: Installers,
             args: argparse.Namespace) -> int:
    try:
        backup = installers.claude_code.install()
    except ClaudeCodeNotFoundError as error:
        print(f"✗ Claude Code not found. {error}")
        return 1
    except UnsupportedPlatformError as error:
        print(f"✗ Not installed: {error}")
        return 1
    except VaultCompatibilityError as error:
        print(f"Not installed: {error}")
        return 1
    print("Claude Code hooks registered; compatible session vaults preserved.")
    _print_backup(backup)
    _install_name_model(installers.name_model, args.model_source)
    return 0


def _install_name_model(setup: NameModelSetup,
                        source: str | None) -> None:
    # Optional: a failure here leaves the protection installed, with names in
    # documents found by the heuristic only. The user must know which case applies.
    try:
        setup.install(source)
    except NameModelSetupError as error:
        print(f"⚠ Name model not installed ({error}).")
        print("  Names in documents are only detected after a label or a title (\"Nom :\", \"Madame\").")
        return
    print("✓ DistilCamemBERT FP32 ready (French person-name detection on documents)")


def _uninstall(installers: Installers,
               args: argparse.Namespace) -> int:
    # The hook goes first: it stops the service that runs inside the model environment.
    backup = installers.claude_code.uninstall()
    installers.name_model.uninstall()
    print("✓ Privacy Guard removed from Claude Code: vaults, service and name model deleted "
          "(logs kept in ~/.privacy-guard/logs)")
    _print_backup(backup)
    return 0


def _status(installers: Installers,
            args: argparse.Namespace) -> int:
    for event, active in installers.claude_code.status().items():
        print(f"  {event:<18} {'registered' if active else 'NOT registered'}")
    model = installers.name_model.status()
    print(f"  {'Name model':<14} {'ready' if all(model.values()) else 'not installed (heuristic only)'}")
    return 0


def _print_backup(backup: Path | None) -> None:
    if backup:
        print(f"  settings.json backup: {backup}")


if __name__ == "__main__":
    sys.exit(main())
