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

from boundary_harness.fake_model import MAIN

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
    # A person's name as file names spell it (cv_camille_lefebvre.md).
    "name-file": "camille_lefebvre",
}

FILES = {
    "customers.csv": "id,full_name,email,phone,iban\n"
                     f"1,{CANARIES['name-1']},{CANARIES['email-1']},{CANARIES['phone-1']},{CANARIES['iban-1']}\n"
                     f"2,{CANARIES['name-2']},{CANARIES['email-2']},,\n",
    "notes.md": "# Suivi client\n\n"
                f"Rendez-vous avec {CANARIES['name-3']} mardi. Contact : {CANARIES['email-2']}.\n",
    ".env": f"APP_ENV=staging\nGITHUB_TOKEN={CANARIES['secret-1']}\n",
    "contacts.py": f'OWNER = "{CANARIES["name-3"]}"\nSUPPORT_EMAIL = "{CANARIES["email-2"]}"\n',
    "seed.sql": "INSERT INTO notes (body, email) VALUES\n"
                f"  ('Rappeler {CANARIES['name-3']} jeudi pour le devis.', '{CANARIES['email-2']}');\n",
    f"cv_{CANARIES['name-file']}.md": "# CV\n\nExpérience : développement Python.\n",
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
    return _write_received_tokens(workspace / "report.md", lambda tokens: "Contacts : " + ", ".join(tokens) + "\n")


def _write_received_tokens(path: Path, render):
    """Step that writes `render(tokens)`, the tokens of the last tool result, to `path`."""
    def step(messages: list) -> list:
        results = [text for message in messages for text in _tool_results(message)]
        received = results[-1] if results else ""
        tokens = list(dict.fromkeys(TOKEN.findall(received)))
        return [("Write", {"file_path": str(path), "content": render(tokens)})]
    return step


def _read_masked_file(workspace: Path):
    """Step that opens the file whose masked name the agent was shown, as an agent would."""
    def step(messages: list) -> list:
        results = [text for message in messages for text in _tool_results(message)]
        listed = (results[-1] if results else "").splitlines()
        masked = next((line.strip() for line in listed if TOKEN.search(line)), "missing.md")
        path = Path(masked) if Path(masked).is_absolute() else workspace / masked
        return [("Read", {"file_path": str(path)})]
    return step


def _read_background_output(messages: list) -> list:
    """Step that reads the output file Claude Code named for a background command."""
    for text in reversed([text for message in messages for text in _tool_results(message)]):
        match = re.search(r"(?:written to|Output file|output file)[^:]*:\s*(\S+)", text)
        if match:
            return [("Read", {"file_path": match.group(1).rstrip(".")})]
    return [("Bash", {"command": "echo no background output file"})]


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
    preserved_file: str | None = None  # must still hold its original canaries after the session
    notes: str = ""
    mcp: bool = False                 # connect the fixture MCP server (mcp_fixture.py)
    resume: list | None = None        # script of a second session resuming the first
    resume_prompt: str | None = None  # its prompt, e.g. "/compact"; the default prompt otherwise
    parallel: int = 1                 # sessions run at the same time in the same profile


def scenarios(workspace: Path) -> list[Scenario]:
    csv, notes, env, contacts, seed = (str(workspace / name)
                                       for name in ("customers.csv", "notes.md", ".env", "contacts.py", "seed.sql"))
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
        Scenario("bash-failure-exit", "installed", False,
                 [[("Bash", {"command": "cat notes.md; exit 3"})], [("Bash", {"command": "cat notes.md || true"})]],
                 notes="An explicit exit is refused before it runs; the agent then rewrites the command."),
        Scenario("powershell-failure-exit", "installed", False,
                 [[("PowerShell", {"command": "Get-Content notes.md; exit 3"})],
                  [("PowerShell", {"command": "Get-Content notes.md"})]],
                 notes="Same refusal for PowerShell exit."),
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
        Scenario("write-python", "installed", False,
                 [[("Read", {"file_path": contacts})],
                  _write_received_tokens(Path(contacts), lambda tokens: "".join(
                      f'VALUE_{index} = "{token}"\n' for index, token in enumerate(tokens))),
                  [("Read", {"file_path": contacts})]],
                 restored_file="contacts.py",
                 notes="Rewriting source code: the values come back on disk, the model keeps tokens."),
        Scenario("write-sql", "installed", False,
                 [[("Read", {"file_path": seed})],
                  _write_received_tokens(Path(seed), lambda tokens: "INSERT INTO notes (body, email) VALUES\n"
                                         + f"  ('Rappeler {tokens[0]} jeudi.', '{tokens[-1]}');\n"),
                  [("Bash", {"command": "cat seed.sql"})]],
                 restored_file="seed.sql",
                 notes="A free-text name in a SQL note needs the name model; values come back escaped."),
        Scenario("write-redacted-secret", "installed", False,
                 [[("Read", {"file_path": env})],
                  _write_received_tokens(Path(env), lambda tokens: "APP_ENV=production\n" + "".join(
                      f"GITHUB_TOKEN={token}\n" for token in tokens))],
                 preserved_file=".env",
                 notes="Rewriting a .env would replace the real secret with its marker: refused."),
        Scenario("subagent-read", "installed", False,
                 {MAIN: [[("Agent", {"description": "Read the notes", "subagent_type": "general-purpose",
                                     "prompt": "SUBAGENT-TASK: read notes.md and report."})]],
                  "SUBAGENT-TASK": [[("Read", {"file_path": notes})]]},
                 notes="The subagent's own conversation and its report to the main agent."),
        Scenario("mcp-result", "installed", False, [[("mcp__fixture__customer_card", {})]], mcp=True),
        # Documented V1 limit (README, Known limits): PostToolUseFailure cannot replace the
        # error and an MCP call cannot be rewritten to succeed. A local MCP relay is V2.
        Scenario("mcp-error", "installed", True, [[("mcp__fixture__customer_lookup_error", {})]], mcp=True,
                 notes="An MCP error takes PostToolUseFailure, like a failing command."),
        Scenario("glob-filenames", "installed", False,
                 [[("Glob", {"pattern": "**/*.md", "path": str(workspace)})]],
                 notes="A person's name inside a file name."),
        Scenario("glob-then-read", "installed", False,
                 [[("Glob", {"pattern": "**/cv_*.md", "path": str(workspace)})], _read_masked_file(workspace)],
                 notes="The agent opens the masked path; file tools get the real one locally."),
        Scenario("edit-document", "installed", False,
                 [[("Read", {"file_path": notes})],
                  [("Edit", {"file_path": notes, "old_string": "mardi", "new_string": "jeudi"})]],
                 notes="Edit returns a snippet of the edited document."),
        Scenario("resume-history", "installed", False, [[("Read", {"file_path": csv})]],
                 resume=[[("Read", {"file_path": csv})], [("Bash", {"command": "echo resumed"})]],
                 notes="A resumed session sends the earlier tool results again."),
        Scenario("background-command", "installed", False,
                 [[("Bash", {"command": "cat notes.md", "run_in_background": True})],
                  [("Bash", {"command": "sleep 2"})], _read_background_output],
                 notes="Output of a background command, read back from its output file."),
        Scenario("compaction", "installed", False, [[("Read", {"file_path": csv})]],
                 resume=[[("Read", {"file_path": csv})]], resume_prompt="/compact",
                 notes="Compaction sends the whole history to the model to summarize it."),
        Scenario("parallel-sessions", "installed", False,
                 [[("Read", {"file_path": csv})], [("Read", {"file_path": notes})]], parallel=3,
                 notes="Three sessions at once share the vault, the journal and the name service."),
        Scenario("hook-in-powershell", "powershell", False, [[("Read", {"file_path": csv})]],
                 notes="No Git Bash: Claude Code runs hooks in PowerShell."),
        Scenario("stalled-name-service", "stalled_service", False, [[("Read", {"file_path": notes})]],
                 notes="Suspended detector: the hook must answer masked before Claude Code's timeout."),
        Scenario("model-unavailable", "model_unavailable", True, [[("Read", {"file_path": notes})]],
                 notes="Founder's option B: names may pass on the heuristic; the warning must be reported."),
        Scenario("hook-timeout", "timeout", True, [[("Read", {"file_path": csv})]],
                 notes="Known platform limit: a timed-out hook's output is discarded."),
        Scenario("hook-launch-error", "launch_error", False, [[("Read", {"file_path": csv})]],
                 notes="Runtime removed: the PreToolUse guard refuses every tool."),
    ]
