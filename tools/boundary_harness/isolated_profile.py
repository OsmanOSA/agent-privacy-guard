"""The TEST-IDENTITY Windows setup installed into a throwaway user profile.

Interface:
    profile = IsolatedProfile.install(setup_exe, root)
    profile.env                    environment where HOME/USERPROFILE/CLAUDE_CONFIG_DIR point inside root
    profile.use_hooks(mode)        installed | absent | powershell | timeout | launch_error
    with profile.hooks(mode):      the same, plus stalled_service for one scenario
    profile.use_engine(package, launcher)   test a source tree with the bundled runtime and model
    profile.use_handler(handler)   register the source tree's hook handler instead of the setup's
    profile.uninstall()

USERPROFILE redirects every ~/.privacy-guard and ~/.claude path of the hook, the
setup and Claude Code itself, so the maintainer's live configuration is never read
or written. Fault modes rewrite only this profile's hook commands.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from boundary_harness.service_control import resume, service_pids, suspend

FAULT_TIMEOUT_SECONDS = 3


class IsolatedProfile:
    def __init__(self, root: Path, app: Path, env: dict):
        self.root, self._app, self.env = root, app, env
        self.home = root / "profile"
        self.settings = self.home / ".claude/settings.json"
        self._installed = None

    @classmethod
    def install(cls, setup: Path, root: Path) -> "IsolatedProfile":
        if not setup.name.startswith("PrivacyGuard-Test-"):
            raise ValueError("Only a --test-build artifact may be installed by the harness")
        home = root / "profile"
        (home / ".claude").mkdir(parents=True)
        env = dict(os.environ, USERPROFILE=str(home), HOME=str(home),
                   CLAUDE_CONFIG_DIR=str(home / ".claude"))
        profile = cls(root, root / "application", env)
        profile._setup(setup, "/S", f"/D={profile._app}")
        notifications = home / ".privacy-guard/notifications/settings.json"
        notifications.write_text('{"version":1,"mode":"off","style":"card"}')
        profile._installed = json.loads(profile.settings.read_text(encoding="utf-8"))
        profile._setup_settings = json.loads(json.dumps(profile._installed))
        profile._run([profile.python, "-m", "privacy_guard.setup", "status"])  # Loads the model once.
        return profile

    @property
    def python(self) -> Path:
        receipt = json.loads((self.home / ".privacy-guard/windows-setup.json").read_text())
        return Path(receipt["bundle"]) / "runtime/python.exe"

    def use_engine(self, package: Path, launcher: Path) -> None:
        """Replace the deployed engine; a fix is measured before a new setup is built.

        The hook runs from ~/.privacy-guard/app, but the bundled runtime's ._pth file
        imports the name service from the bundle's own app directory: both are replaced.
        """
        app = self.home / ".privacy-guard/app"
        for target in (app, self.python.parent.parent / "app"):
            if not (target / package.name).is_dir():
                raise RuntimeError(f"No deployed engine in {target}")
            shutil.rmtree(target / package.name)
            shutil.copytree(package, target / package.name, ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copy2(launcher, target / "__main__.py")
        # The setup's status check started the name service with the old code.
        stop = ("from privacy_guard.service.channel import DEFAULT_RUN_DIR, ServiceChannel; "
                "from privacy_guard.service.client import ServiceClient; "
                "ServiceClient(ServiceChannel(DEFAULT_RUN_DIR)).stop()")
        subprocess.run([str(self.python), "-c", stop], cwd=app, env=self.env, capture_output=True, timeout=60)

    def use_handler(self, handler: dict) -> None:
        """Register a source handler in place of the setup's own entries (fresh profile: all ours)."""
        for groups in self._installed.get("hooks", {}).values():
            for group in groups:
                group["hooks"] = [dict(handler) for _ in group["hooks"]]

    @contextmanager
    def hooks(self, mode: str):
        """Hook mode for one scenario; `stalled_service` suspends a running name service."""
        if mode != "stalled_service":
            self.use_hooks(mode)
            yield
            return
        self.use_hooks("installed")
        self._run([self.python, "-m", "privacy_guard.setup", "status"])  # Starts the service.
        pids = service_pids(self.home)
        if not pids:
            raise RuntimeError("No name service to stall")
        suspend(pids)
        try:
            yield
        finally:
            resume(pids)

    def use_hooks(self, mode: str) -> None:
        settings = json.loads(json.dumps(self._installed))
        handlers = [hook for groups in settings.get("hooks", {}).values() for group in groups for hook in group["hooks"]]
        if mode == "absent":
            settings.pop("hooks", None)
        elif mode == "powershell":
            # Without Git Bash, Claude Code runs hooks in PowerShell.
            for hook in handlers:
                hook["shell"] = "powershell"
        elif mode in {"timeout", "launch_error"}:
            command, args = ((self.python.as_posix(), ["-c", "import time; time.sleep(60)"]) if mode == "timeout"
                             else ((self.root / "missing/python.exe").as_posix(), ["app"]))
            for hook in handlers:
                hook.update(command=command, args=args, timeout=FAULT_TIMEOUT_SECONDS)
        elif mode != "installed":
            raise ValueError(f"Unknown hook mode: {mode}")
        self.settings.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    def uninstall(self) -> None:
        # The setup under test removes only the entries it wrote itself.
        self.settings.write_text(json.dumps(self._setup_settings, indent=2), encoding="utf-8")
        self._setup(self._app / "Uninstall.exe", "/S", f"_?={self._app}")
        receipt = self.home / ".privacy-guard/windows-setup.json"
        deadline = time.monotonic() + 15
        while receipt.exists() and time.monotonic() < deadline:
            time.sleep(.1)

    def _setup(self, executable: Path, *arguments: str) -> None:
        # NSIS /D and _? consume the remainder verbatim, without enclosing quotes.
        command = subprocess.list2cmdline([str(executable), *arguments[:-1]]) + " " + arguments[-1]
        self._run(command)

    def _run(self, command) -> None:
        result = subprocess.run(command if isinstance(command, str) else list(map(str, command)),
                                env=self.env, capture_output=True, timeout=300)
        if result.returncode:
            log = Path(tempfile.gettempdir()) / "PrivacyGuardSetupTest-setup-error.txt"
            detail = (log.read_text(encoding="utf-16-le") if log.exists()
                      else result.stderr.decode("utf-8", errors="replace"))
            raise RuntimeError(f"Setup step failed ({result.returncode}): {detail}")
