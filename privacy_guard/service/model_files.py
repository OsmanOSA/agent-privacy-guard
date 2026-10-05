"""The converted name model files, verified before use.

The service executes model.onnx: a corrupted or tampered file must never be
loaded. Every file is checked against the SHA-256 of the validated build, both
when it is fetched and whenever readiness is checked.

Interface:
    files = ModelFiles(directory)
    files.is_ready() / files.fetch(source) / files.remove()

A source is a local directory or an https:// base URL holding the three files.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import urllib.request
from pathlib import Path

from privacy_guard.fs import remove_tree

DEFAULT_MODEL_DIR = Path.home() / ".privacy-guard" / "models" / "person-ner"
# SHA-256 of the build validated against GLiNER2 (tools/validate_name_model.py).
# A new build gets new hashes: update them together with the published files.
MANIFEST = {
    "config.json": "01d25ede6088515d8fb88445a626c52802c9e5748be23c10ebf5a43938df47ab",
    "model.onnx": "a0da9404e04da3b832f89cd92f81fc9d3fe8a160d8f645fae57805b7efc71986",
    "tokenizer.json": "f6df10ec83bea993035b2dd7c39345a3d4fcf23421c2adb6cb4ffc1e6d1bc4b5",
}
DOWNLOAD_TIMEOUT_SECONDS = 60
CHUNK_BYTES = 1 << 20


class ModelFilesError(RuntimeError):
    """The model could not be fetched, or a file does not match its expected hash."""


class ModelFiles:
    """Fetches and verifies the files of the converted name model."""

    def __init__(self, directory: Path = DEFAULT_MODEL_DIR,
                 manifest: dict[str, str] = MANIFEST) -> None:
        self._directory = directory
        self._manifest = manifest

    def is_ready(self) -> bool:
        """True when every file is present with its expected hash."""
        return all(_sha256(self._directory / name) == digest for name, digest in self._manifest.items())

    def fetch(self, source: str) -> None:
        """Copies or downloads every file, verifies it, then installs them together.

        Raises ModelFilesError; the installed model is left untouched on failure.
        """
        self._directory.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self._directory.parent) as staging:
            staging_dir = Path(staging)
            for name, digest in self._manifest.items():
                _retrieve(source, name, staging_dir / name)
                if _sha256(staging_dir / name) != digest:
                    raise ModelFilesError(f"{name} does not match the validated model (SHA-256 mismatch)")
            self.remove()
            shutil.copytree(staging_dir, self._directory)

    def remove(self) -> None:
        remove_tree(self._directory)


def _retrieve(source: str,
              name: str,
              target: Path) -> None:
    if source.startswith("https://"):
        _download(f"{source.rstrip('/')}/{name}", target)
    elif source.startswith(("http://", "ftp://")):
        raise ModelFilesError("Only https:// sources are accepted")
    else:
        source_file = Path(source) / name
        if not source_file.is_file():
            raise ModelFilesError(f"{source_file} not found")
        shutil.copyfile(source_file, target)


def _download(url: str,
              target: Path) -> None:
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response, target.open("wb") as file:
            shutil.copyfileobj(response, file, CHUNK_BYTES)
    except OSError as error:
        raise ModelFilesError(f"Download failed for {url}: {error}") from error


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()
