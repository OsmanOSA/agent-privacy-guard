"""Observe what a real Claude Code session sends to the model, with Privacy Guard installed.

Installs a TEST-IDENTITY setup into an isolated profile, runs scripted headless
sessions against a local fake Messages API, and checks that no synthetic canary
crosses that boundary. Prints a receipt containing canary ids only.

    python tools/check_model_boundary.py dist/PrivacyGuard-Test-....exe --work DIR [--source]

--source replaces the setup's hook engine with this checkout, keeping the bundled
runtime and model, so a fix is measured before a new setup is built.
"""

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from boundary_harness.isolated_profile import IsolatedProfile
from boundary_harness.scenarios import scenarios
from boundary_harness.session import run_scenario

REPOSITORY = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("setup", type=Path)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--claude", default=shutil.which("claude"))
    parser.add_argument("--only", nargs="*", help="Scenario ids to run")
    parser.add_argument("--source", action="store_true", help="Test this checkout's hook engine")
    args = parser.parse_args()
    root = args.work.resolve()
    root.mkdir(parents=True, exist_ok=False)
    records, workspace = root / "records", root / "workspace"
    records.mkdir()
    selected = [s for s in scenarios(workspace) if not args.only or s.id in args.only]

    profile = IsolatedProfile.install(args.setup.resolve(), root)
    try:
        if args.source:
            profile.use_engine(REPOSITORY / "privacy_guard",
                               REPOSITORY / "privacy_guard/claude_code/launcher.py")
            profile.use_handlers(source_handlers(profile))
        outcomes = [run_scenario(s, profile, workspace, records, args.claude) for s in selected]
    finally:
        profile.uninstall()
    receipt = {"environment": {**environment(args.claude, args.setup), "engine": engine(args.source)},
               "outcomes": outcomes}
    (root / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))


def environment(claude: str, setup: Path) -> dict:
    version = subprocess.run([claude, "--version"], capture_output=True, text=True).stdout.strip()
    return {"claude_code": version, "windows": platform.version(), "setup": setup.name}


def source_handlers(profile: IsolatedProfile) -> dict:
    """The hook handlers this checkout's installer would register for the profile."""
    sys.path.insert(0, str(REPOSITORY))
    from privacy_guard.claude_code.registration import hook_handlers
    return hook_handlers(profile.python.as_posix(), (profile.home / ".privacy-guard/app").as_posix())


def engine(source: bool) -> str:
    if not source:
        return "setup"
    git = ["git", "-C", str(REPOSITORY)]
    commit = subprocess.run(git + ["rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(git + ["status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    return f"source {commit}{' + uncommitted changes' if dirty else ''}"


if __name__ == "__main__":
    main()
