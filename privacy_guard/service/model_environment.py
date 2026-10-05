"""The Python environment that runs the name model in the background service.

A dedicated virtual environment with the three packages the ONNX detector needs,
pinned to the versions it was validated with. The hook itself stays stdlib-only;
only the service runs with this environment's Python.

Interface:
    environment = ModelEnvironment(directory)
    environment.is_ready() / environment.create() / environment.remove()
    environment.python   (the interpreter the service is launched with)
"""

from __future__ import annotations

import json
import subprocess
import sys
import venv
from pathlib import Path

from privacy_guard.fs import remove_tree

DEFAULT_MODEL_ENV = Path.home() / ".privacy-guard" / "model-env"
# Validated with tools/validate_name_model.py: change only together with a new validation.
REQUIREMENTS = ("numpy==2.5.3", "onnxruntime==1.30.0", "tokenizers==0.22.2")
# Written last: an environment without it was interrupted and is rebuilt from scratch.
MARKER_FILE = "privacy-guard-requirements.json"
PIP_TIMEOUT_SECONDS = 600


class ModelEnvironmentError(RuntimeError):
    """The environment could not be created (no network, no disk space...)."""


class ModelEnvironment:
    """Creates and checks the virtual environment of the name model."""

    def __init__(self, directory: Path = DEFAULT_MODEL_ENV,
                 requirements: tuple[str, ...] = REQUIREMENTS) -> None:
        self._directory = directory
        self._requirements = requirements

    @property
    def python(self) -> Path:
        scripts = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
        return self._directory / scripts

    def is_ready(self) -> bool:
        """True when the environment exists with exactly the pinned packages."""
        marker = self._directory / MARKER_FILE
        return (self.python.exists() and marker.exists()
                and json.loads(marker.read_text(encoding="utf-8")) == list(self._requirements))

    def create(self) -> None:
        """Builds the environment from scratch. Raises ModelEnvironmentError on failure."""
        self.remove()
        venv.EnvBuilder(with_pip=bool(self._requirements)).create(self._directory)
        if self._requirements:
            self._install_requirements()
        (self._directory / MARKER_FILE).write_text(json.dumps(list(self._requirements)), encoding="utf-8")

    def remove(self) -> None:
        remove_tree(self._directory)

    def _install_requirements(self) -> None:
        command = [str(self.python), "-m", "pip", "install", "--disable-pip-version-check",
                   "--no-input", "--quiet", *self._requirements]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=PIP_TIMEOUT_SECONDS)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            details = getattr(error, "stderr", "") or ""
            raise ModelEnvironmentError(f"pip failed: {details.strip()[-300:]}") from error
