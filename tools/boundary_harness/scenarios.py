"""Synthetic canaries, the workspace that holds them and the scripted agent sessions.

Interface:
    CANARIES                  id -> synthetic value that must never reach the model
    write_workspace(path)     creates the fixture files
    SCENARIOS                 list of Scenario (id, hook mode, script, expected outcome)

Evidence keeps canary ids only: values are synthetic, but a receipt full of
personal-looking data would be indistinguishable from a real leak.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass
from pathlib import Path

# Pseudonyms carry an id; secrets are masked without one.
TOKEN = re.compile(r"⟦[A-Z_]+:(?:[0-9A-F]{8}|REDACTED)⟧")


def _iban(country: str, bban: str) -> str:
    digits = "".join(str(int(char, 36)) for char in bban + country + "00")
    return f"{country}{98 - int(digits) % 97:02d}{bban}"


def _github_token() -> str:
    # Assembled at runtime so secret scanners do not flag the source as a credential.
    body = (string.ascii_letters + string.digits)[7:43]
    return "ghp" + "_" + body


CANARIES = {
    "name-1": "Camille Lefebvre",
    "name-2": "Julien Moreau",
    "name-3": "Nathalie Garnier",
    "email-1": "c.lefebvre@exemple-client.fr",
    "email-2": "julien.moreau@exemple-client.fr",
    "phone-1": "06 41 27 85 93",
    "iban-1": _iban("FR", "30006000011234567890189"),
    "secret-1": _github_token(),
}

FILES = {
    "customers.csv": "id,full_name,email,phone,iban\n"
                     f"1,{CANARIES['name-1']},{CANARIES['email-1']},{CANARIES['phone-1']},{CANARIES['iban-1']}\n"
                     f"2,{CANARIES['name-2']},{CANARIES['email-2']},,\n",
    "notes.md": "# Suivi client\n\n"
                f"Rendez-vous avec {CANARIES['name-3']} mardi. Contact : {CANARIES['email-2']}.\n",
    ".env": f"APP_ENV=staging\nGITHUB_TOKEN={CANARIES['secret-1']}\n",
}


# Windows tools often emit cp1252 bytes; one undecodable byte used to fail the name model.
LEGACY_FILE = "legacy.txt", f"Réunion avec {CANARIES['name-1']} à Lyon.\n".encode("cp1252")


def write_workspace(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for name, content in FILES.items():
        (path / name).write_text(content, encoding="utf-8")
    (path / LEGACY_FILE[0]).write_bytes(LEGACY_FILE[1])


def _report_from_last_result(workspace: Path):
    """Step that writes the tokens the agent received into a new local document."""
    def step(messages: list) -> list:
        results = [text for message in messages for text in _tool_results(message)]
        received = results[-1] if results else ""
        tokens = list(dict.fromkeys(TOKEN.findall(received)))
        content = "Contacts : " + ", ".join(tokens) + "\n"
        return [("Write", {"file_path": str(workspace / "report.md"), "content": content})]
    return step


def _tool_results(message: dict) -> list:
    texts = []
    for block in message.get("content") or ():
        if isinstance(block, dict) and block.get("type") == "tool_result":
            content = block.get("content")
            parts = content if isinstance(content, list) else [{"text": content}]
            texts += [part.get("text") or "" for part in parts if isinstance(part, dict)]
    return texts


@dataclass
class Scenario:
    id: str
    hook: str            # installed | absent | timeout | launch_error
    expect_leak: bool    # True for the sensitivity control and known platform limits
    script: list
    restored_file: str | None = None
    notes: str = ""


def scenarios(workspace: Path) -> list[Scenario]:
    csv, notes, env = (str(workspace / name) for name in ("customers.csv", "notes.md", ".env"))
    return [
        Scenario("control-unprotected-read", "absent", True, [[("Read", {"file_path": csv})]],
                 notes="Harness sensitivity: without hooks the canaries must be observed."),
        Scenario("read-csv", "installed", False, [[("Read", {"file_path": csv})]]),
        Scenario("bash-cat", "installed", False, [[("Bash", {"command": "cat customers.csv"})]]),
        Scenario("grep-content", "installed", False,
                 [[("Grep", {"pattern": "@", "path": str(workspace), "output_mode": "content"})]]),
        Scenario("bash-failure-status", "installed", False, [[("Bash", {"command": "cat notes.md && false"})]],
                 notes="Failing command: rerouted from PostToolUseFailure to PostToolUse."),
        Scenario("bash-failure-grep", "installed", False,
                 [[("Bash", {"command": "grep -n Rendez notes.md missing.txt"})]],
                 notes="Realistic failure: one operand missing, matches printed before exit status 2."),
        Scenario("bash-failure-exit", "installed", False, [[("Bash", {"command": "cat notes.md; exit 3"})]],
                 notes="Residual: an explicit exit ends the shell before the trailer runs."),
        Scenario("powershell-get-content", "installed", False,
                 [[("PowerShell", {"command": "Get-Content customers.csv"})]]),
        Scenario("powershell-failure", "installed", False,
                 [[("PowerShell", {"command": "Get-Content notes.md; Get-Content missing.txt"})]],
                 notes="Non-terminating error after printing the document."),
        Scenario("powershell-notes", "installed", False,
                 [[("PowerShell", {"command": "Get-Content notes.md"})]],
                 notes="Free text through the primary Windows shell: names need the model."),
        Scenario("bash-cp1252", "installed", False, [[("Bash", {"command": "cat legacy.txt"})]],
                 notes="Undecodable bytes must not blind the agent nor leak the name."),
        Scenario("parallel-reads", "installed", False,
                 [[("Read", {"file_path": csv}), ("Read", {"file_path": notes})]]),
        Scenario("secret-env", "installed", False, [[("Read", {"file_path": env})]]),
        Scenario("write-restore-reread", "installed", False,
                 [[("Read", {"file_path": notes})], _report_from_last_result(workspace),
                  [("Read", {"file_path": str(workspace / "report.md")})]],
                 restored_file="report.md",
                 notes="Restored originals on disk; agent context must still hold tokens only."),
        Scenario("hook-in-powershell", "powershell", False, [[("Read", {"file_path": csv})]],
                 notes="No Git Bash: Claude Code runs hooks in PowerShell."),
        Scenario("hook-timeout", "timeout", True, [[("Read", {"file_path": csv})]],
                 notes="Known platform limit: a timed-out hook's output is discarded."),
        Scenario("hook-launch-error", "launch_error", True, [[("Read", {"file_path": csv})]],
                 notes="Hook command cannot start (missing runtime)."),
    ]
