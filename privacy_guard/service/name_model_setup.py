"""Installation of the name model: its Python environment and its verified files.

Optional by design: without it, protection still works and names in documents
are found by the heuristic only. The installer reports which case applies.

Interface:
    setup = NameModelSetup(guard_home)
    setup.install(source)   -> raises NameModelSetupError with a readable reason
    setup.status()          -> {"environment": bool, "model": bool}
    setup.uninstall()
"""

from __future__ import annotations

from pathlib import Path

from privacy_guard.service.model_environment import ModelEnvironment, ModelEnvironmentError
from privacy_guard.service.model_files import ModelFiles, ModelFilesError
from privacy_guard.service.distil_files import DISTIL_DIRECTORY, MANIFEST
from privacy_guard.service.ner_policy import record_model, remove_model

# Prepared bundle source, including the pinned upstream card and tokenizer.
# No hosted converted bundle is configured; use tools/prepare_distil_bundle.py.
DEFAULT_MODEL_SOURCE: str | None = None


class NameModelSetupError(RuntimeError):
    """The name model could not be installed; protection runs without it."""


class NameModelSetup:
    """Installs, checks and removes everything the name model needs."""

    def __init__(self, guard_home: Path) -> None:
        self._home = guard_home
        self._environment = ModelEnvironment(guard_home / "model-env")
        self._files = ModelFiles(guard_home / "models" / DISTIL_DIRECTORY, MANIFEST)

    def install(self, source: str | None = DEFAULT_MODEL_SOURCE) -> None:
        """Brings the environment and the files to the validated state. Idempotent and cheap when ready."""
        try:
            if not self._environment.is_ready():
                self._environment.create()
            if not self._files.is_ready():
                if source is None:
                    raise ModelFilesError("model files missing: install with --model-source DIRECTORY_OR_HTTPS_URL")
                self._files.fetch(source)
            record_model(self._home)
        except (ModelEnvironmentError, ModelFilesError, OSError) as error:
            raise NameModelSetupError(str(error)) from error

    def status(self) -> dict[str, bool]:
        return {"environment": self._environment.is_ready(), "model": self._files.is_ready()}

    def uninstall(self) -> None:
        self._environment.remove()
        self._files.remove()
        remove_model(self._home)
