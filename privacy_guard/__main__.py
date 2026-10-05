"""Privacy Guard command line.

Usage, from the project root:
    python -m privacy_guard install [--model-source DIRECTORY_OR_HTTPS_URL]
    python -m privacy_guard status
    python -m privacy_guard uninstall
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from privacy_guard.claude_code.installer import ClaudeCodeInstaller, ClaudeCodeNotFoundError
from privacy_guard.core.cipher import UnsupportedPlatformError
from privacy_guard.service.name_model_setup import DEFAULT_MODEL_SOURCE, NameModelSetup, NameModelSetupError


@dataclass(frozen=True)
class Installers:
    """Everything the command line drives: the Claude Code hook and the optional name model."""

    claude_code: ClaudeCodeInstaller
    name_model: NameModelSetup


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = _parse_args(argv)
    installers = Installers(
        ClaudeCodeInstaller(args.claude_dir, args.guard_home, Path(sys.executable)),
        NameModelSetup(args.guard_home),
    )
    actions = {"install": _install, "uninstall": _uninstall, "status": _status}
    return actions[args.action](installers, args)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="privacy_guard", description="Privacy Guard for Claude Code")
    parser.add_argument("action", nargs="?", default="status", choices=["install", "uninstall", "status"])
    parser.add_argument("--claude-dir", type=Path, default=Path.home() / ".claude")
    parser.add_argument("--guard-home", type=Path, default=Path.home() / ".privacy-guard")
    parser.add_argument("--model-source", default=DEFAULT_MODEL_SOURCE,
                        help="directory or https:// URL holding the converted name model")
    return parser.parse_args(argv)


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
    print("✓ Claude Code protected (every tool call; vault cleared when the session ends)")
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
    print("✓ Name model ready (names detected anywhere in documents)")


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
        print(f"  {event:<14} {'protected' if active else 'NOT protected'}")
    model = installers.name_model.status()
    print(f"  {'Name model':<14} {'ready' if all(model.values()) else 'not installed (heuristic only)'}")
    return 0


def _print_backup(backup: Path | None) -> None:
    if backup:
        print(f"  settings.json backup: {backup}")


if __name__ == "__main__":
    sys.exit(main())
