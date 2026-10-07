"""Explicit per-user notification preference. Missing config means off."""

import json
import os
import uuid
from pathlib import Path

MODES = {"off", "background", "always"}
STYLES = {"card", "native"}


def read_mode(directory: Path) -> str:
    return read_preferences(directory)["mode"]


def read_style(directory: Path) -> str:
    return read_preferences(directory)["style"]


def read_preferences(directory: Path) -> dict:
    default = {"mode": "off", "style": "card"}
    try:
        path = directory / "settings.json"
        if path.stat().st_size > 1024:
            return default
        row = json.loads(path.read_text(encoding="utf-8"))
        mode = row.get("mode")
        if row.get("version") != 1 or mode not in MODES:
            return default
        style = row.get("style", "card")
        return {"mode": mode, "style": style if style in STYLES else "native"}
    except (OSError, ValueError, AttributeError, TypeError):
        return default


def configure(directory: Path, mode: str, style=None):
    if mode not in MODES:
        raise ValueError("Invalid notification mode")
    style = read_style(directory) if style is None else style
    if style not in STYLES:
        raise ValueError("Invalid notification style")
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / (uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps({"version": 1, "mode": mode, "style": style}), encoding="utf-8")
        os.replace(temporary, directory / "settings.json")
    finally:
        temporary.unlink(missing_ok=True)
