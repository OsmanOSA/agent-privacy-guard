"""Installation of Privacy Guard into Claude Code.

Install = deploy the engine to ~/.privacy-guard/app, then register the hook in
~/.claude/settings.json. Uninstall = the reverse. The rest of the user's
configuration is never modified.

Compatible updates preserve session vaults and their token identifiers. Unknown
formats stop installation without deleting data. Uninstall purges the vaults.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import privacy_guard
from privacy_guard.claude_code import registration
from privacy_guard.claude_code.settings_file import SettingsFile
from privacy_guard.claude_code.vault_format import VaultCompatibility
from privacy_guard.core.cipher import default_cipher
from privacy_guard.fs import remove_tree
from privacy_guard.service.channel import ServiceChannel
from privacy_guard.service.client import ServiceClient
from privacy_guard.notifications.lifecycle import stop_worker

PACKAGE_DIR = Path(privacy_guard.__file__).resolve().parent
LAUNCHER_FILE = PACKAGE_DIR / "claude_code" / "launcher.py"


class ClaudeCodeNotFoundError(RuntimeError):
    """Claude Code is not installed on this machine."""


class ClaudeCodeInstaller:
    """Installs, removes and checks Privacy Guard protection for Claude Code."""

    def __init__(self, claude_dir: Path, guard_home: Path, python: Path) -> None:
        self._claude_dir = claude_dir
        self._app_dir = guard_home / "app"
        self._vault_dir = guard_home / "vault"
        self._run_dir = guard_home / "run"
        self._notification_dir = guard_home / "notifications"
        self._python = python
        self._settings = SettingsFile(claude_dir / "settings.json")
        self._vault_format = VaultCompatibility(guard_home, PACKAGE_DIR)
        self._service = ServiceClient(ServiceChannel(self._run_dir))

    def install(self) -> Path | None:
        """Deploys the engine and registers the hook. Returns the settings.json backup.

        Raises ClaudeCodeNotFoundError, or UnsupportedPlatformError where the
        vault cannot be encrypted: better no install than secrets in clear on disk.
        """
        if not self._claude_dir.is_dir():
            raise ClaudeCodeNotFoundError(f"Directory not found: {self._claude_dir}")
        default_cipher()
        self._vault_format.check()
        # The running service still executes the previous version: stop it first.
        self._service.stop()
        stop_worker(self._notification_dir)
        self._deploy_app()
        backup = self._update_settings(registration.register(self._settings.load(), self._hook_command()))
        self._vault_format.record()
        return backup

    def uninstall(self) -> Path | None:
        """Removes the hook, the service, the deployed engine and the vaults.
        Returns the settings.json backup."""
        backup = self._update_settings(registration.unregister(self._settings.load()))
        self._service.stop()
        stop_worker(self._notification_dir)
        for directory in (self._app_dir, self._vault_dir, self._run_dir):
            remove_tree(directory)
        self._vault_format.clear()
        return backup

    def status(self) -> dict[str, bool]:
        """Tells, for each event, whether protection is active."""
        return registration.registered_events(self._settings.load())

    def _deploy_app(self) -> None:
        # Start from a clean directory so no file from a previous version remains.
        remove_tree(self._app_dir)
        for source in PACKAGE_DIR.rglob("*.py"):
            self._copy_file(source, self._app_dir / PACKAGE_DIR.name / source.relative_to(PACKAGE_DIR))
        self._copy_file(LAUNCHER_FILE, self._app_dir / "__main__.py")


    @staticmethod
    def _copy_file(source: Path, target: Path) -> None:
        # copyfile copies content only, not permissions: synced folders (OneDrive)
        # are read-only and would make the deployment impossible to delete.
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    def _hook_command(self) -> str:
        # Forward slashes: Claude Code runs hooks through a bash shell, Windows included.
        return f'"{self._python.as_posix()}" "{self._app_dir.as_posix()}"'

    def _update_settings(self, updated: dict) -> Path | None:
        # No write (and no backup) when nothing changes.
        if updated == self._settings.load():
            return None
        return self._settings.save(updated)
