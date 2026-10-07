"""One headless Claude Code session against the fake model, and its verdict.

Interface:
    outcome = run_scenario(scenario, profile, workspace, record_dir, claude)
    outcome -> dict with canary ids only: leaked ids, token count, completion, verdict.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from boundary_harness.fake_model import FINAL_TEXT, FakeModel
from boundary_harness.scenarios import CANARIES, TOKEN, write_workspace

PROMPT = "Run the scripted fixture check."
SESSION_TIMEOUT_SECONDS = 300


def agent_env(base: dict, base_url: str) -> dict:
    """The profile's environment, with any outer agent session or credential removed."""
    env = {key: value for key, value in base.items()
           if not key.startswith(("ANTHROPIC_", "CLAUDE_CODE_", "CLAUDECODE"))}
    env.update(ANTHROPIC_BASE_URL=base_url, ANTHROPIC_API_KEY="harness-offline-key",
               CLAUDE_CONFIG_DIR=base["CLAUDE_CONFIG_DIR"],
               # On by default for claude.ai accounts on Windows, where it is the primary shell.
               CLAUDE_CODE_USE_POWERSHELL_TOOL="1",
               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1", DISABLE_AUTOUPDATER="1",
               DISABLE_TELEMETRY="1", DISABLE_ERROR_REPORTING="1")
    return env


def observed_strings(record: Path) -> list[str]:
    """Every string the agent sent to the model, decoded from the recorded bodies."""
    found = []

    def walk(value):
        if isinstance(value, str):
            found.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    if record.exists():
        for line in record.read_text(encoding="utf-8").splitlines():
            walk(json.loads(line)["body"])
    return found


def leaked_ids(texts: list[str]) -> list[str]:
    return sorted(cid for cid, value in CANARIES.items() if any(value in text for text in texts))


def run_scenario(scenario, profile, workspace: Path, record_dir: Path, claude: str) -> dict:
    shutil.rmtree(workspace, ignore_errors=True)
    write_workspace(workspace)
    profile.use_hooks(scenario.hook)
    record = record_dir / f"{scenario.id}.jsonl"
    with FakeModel(scenario.script, record) as model:
        command = [claude, "-p", PROMPT, "--output-format", "json",
                   "--dangerously-skip-permissions", "--max-turns", "8"]
        result = subprocess.run(command, cwd=workspace, env=agent_env(profile.env, model.base_url),
                                capture_output=True, timeout=SESSION_TIMEOUT_SECONDS)
    (record_dir / f"{scenario.id}.agent.json").write_bytes(result.stdout + b"\n" + result.stderr)
    texts = observed_strings(record)
    leaked = leaked_ids(texts)
    outcome = {"scenario": scenario.id, "hook": scenario.hook, "expect_leak": scenario.expect_leak,
               "agent_exit": result.returncode, "requests": _count_lines(record) if record.exists() else 0,
               "completed": _completed(result.stdout), "tokens_seen": len(set(TOKEN.findall("\n".join(texts)))),
               "leaked": leaked}
    if scenario.restored_file:
        restored = (workspace / scenario.restored_file)
        content = restored.read_text(encoding="utf-8") if restored.exists() else ""
        outcome["restored_on_disk"] = leaked_ids([content])
    outcome["verdict"] = _verdict(scenario, outcome)
    return outcome


def _verdict(scenario, outcome: dict) -> str:
    if outcome["requests"] == 0:
        return "inconclusive: no model request recorded"
    if scenario.expect_leak:
        return "as expected (leak observed)" if outcome["leaked"] else "unexpected: no leak observed"
    if outcome["leaked"]:
        return "FAIL: canary reached the model"
    if not outcome["tokens_seen"]:
        return "inconclusive: no protected token observed"
    if scenario.restored_file and not outcome.get("restored_on_disk"):
        return "FAIL: local file not restored"
    return "pass"


def _completed(stdout: bytes) -> bool:
    try:
        return json.loads(stdout).get("result") == FINAL_TEXT
    except (ValueError, AttributeError):
        return False


def _count_lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())
