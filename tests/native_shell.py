"""Run native Windows hook tests through Git Bash rather than WSL bash."""

import shutil
import sys
from pathlib import Path


def native_bash():
    if sys.platform != "win32":
        return shutil.which("bash")
    git = shutil.which("git")
    if git:
        for parent in Path(git).resolve().parents[:3]:
            candidate = parent / "bin" / "bash.exe"
            if candidate.is_file():
                return str(candidate)
    raise RuntimeError("Native Windows hook tests require Git Bash; WSL is a separate unsupported combination")
