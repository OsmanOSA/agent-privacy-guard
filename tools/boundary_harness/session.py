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
import sys
import time
import zipfile
from contextlib import ExitStack
from pathlib import Path

from boundary_harness.fake_model import FINAL_TEXT, FakeModel
from boundary_harness.scenarios import CANARIES, FILES, TOKEN, write_workspace

PROMPT = "Run the scripted fixture check."
# The hook's fail-closed replacement (claude_code/tool_failures.py).
MASKED = "[Privacy Guard: Output masked; inspection failed.]"
# How Claude Code reports a PreToolUse refusal to the model (2.1.292).
REFUSED = "PreToolUse:"
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
    record = record_dir / f"{scenario.id}.jsonl"
    journal = profile.home / ".privacy-guard/logs/protection.jsonl"
    journal_start = journal.stat().st_size if journal.exists() else 0
    started = time.monotonic()
    extra = _mcp_arguments(record_dir) if scenario.mcp else []
    with profile.hooks(scenario.hook):
        if scenario.parallel > 1:
            result = _parallel_agents(scenario, claude, workspace, profile.env, record, extra)
        else:
            with FakeModel(scenario.script, record) as model:
                result = _agent(claude, workspace, agent_env(profile.env, model.base_url), extra)
        if scenario.resume is not None:
            # The resumed history is sent to the model again: it must hold tokens only.
            session_id = json.loads(result.stdout)["session_id"]
            with FakeModel(scenario.resume, record) as model:
                result = _agent(claude, workspace, agent_env(profile.env, model.base_url),
                                extra + ["--resume", session_id], scenario.resume_prompt or PROMPT)
    elapsed = round(time.monotonic() - started, 1)
    (record_dir / f"{scenario.id}.agent.json").write_bytes(result.stdout + b"\n" + result.stderr)
    texts = observed_strings(record)
    leaked = leaked_ids(texts)
    outcome = {"scenario": scenario.id, "hook": scenario.hook, "expect_leak": scenario.expect_leak,
               "agent_exit": result.returncode, "requests": _count_lines(record) if record.exists() else 0,
               "completed": _completed(result.stdout), "tokens_seen": len(set(TOKEN.findall("\n".join(texts)))),
               "masked": any(MASKED in text for text in texts), "seconds": elapsed, "leaked": leaked,
               "refused": any(REFUSED in text for text in texts),
               "reduced_reported": _reduced_reported(journal, journal_start)}
    if scenario.restored_file:
        content = _disk_text(workspace / scenario.restored_file)
        outcome["restored_on_disk"] = leaked_ids([content])
    if scenario.preserved_file:
        kept = workspace / scenario.preserved_file
        content = kept.read_text(encoding="utf-8") if kept.exists() else ""
        outcome["preserved_on_disk"] = leaked_ids([content]) == leaked_ids([FILES[scenario.preserved_file]])
    outcome["verdict"] = _verdict(scenario, outcome)
    return outcome


def _disk_text(path: Path) -> str:
    """A file's text as stored on disk; a workbook's shared strings."""
    if not path.exists():
        return ""
    if path.suffix == ".xlsx":
        with zipfile.ZipFile(path) as book:
            return book.read("xl/sharedStrings.xml").decode("utf-8")
    return path.read_text(encoding="utf-8")


def _verdict(scenario, outcome: dict) -> str:
    if outcome["requests"] == 0:
        return "inconclusive: no model request recorded"
    if scenario.hook == "model_unavailable":
        # Option B accepts missed names, never missed formatted data nor a silent reduction.
        if any(not canary.startswith("name-") for canary in outcome["leaked"]):
            return "FAIL: non-name canary reached the model"
        return "pass: reduced detection reported" if outcome["reduced_reported"] else "FAIL: reduction not reported"
    if scenario.expect_leak:
        return "as expected (leak observed)" if outcome["leaked"] else "unexpected: no leak observed"
    if outcome["leaked"]:
        return "FAIL: canary reached the model"
    if scenario.preserved_file and not outcome["preserved_on_disk"]:
        return "FAIL: local file lost its original values"
    if not outcome["tokens_seen"] and not outcome["masked"]:
        # The hook may stop the session before the result is sent: nothing reached the model.
        if not outcome["completed"]:
            return "pass: session stopped before the result was sent"
        if outcome["refused"]:
            return "pass: tool refused before it ran"
        return "inconclusive: no protected token observed"
    if scenario.restored_file and not outcome.get("restored_on_disk"):
        return "FAIL: local file not restored"
    return "pass"


def _agent(claude: str, workspace: Path, env: dict, extra: list, prompt: str = PROMPT) -> subprocess.CompletedProcess:
    return subprocess.run(_command(claude, extra, prompt), cwd=workspace, env=env, capture_output=True,
                          timeout=SESSION_TIMEOUT_SECONDS)


def _command(claude: str, extra: list, prompt: str = PROMPT) -> list:
    return [claude, "-p", prompt, "--output-format", "json", "--dangerously-skip-permissions",
            "--max-turns", "8", *extra]


def _parallel_agents(scenario, claude, workspace, profile_env, record, extra) -> subprocess.CompletedProcess:
    """Sessions started together in one profile: they share the vault, journal and name service."""
    records = [record.with_name(f"{record.stem}.{index}.jsonl") for index in range(scenario.parallel)]
    with ExitStack() as stack:
        models = [stack.enter_context(FakeModel(scenario.script, path)) for path in records]
        processes = [subprocess.Popen(_command(claude, extra), cwd=workspace,
                                      env=agent_env(profile_env, model.base_url),
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE) for model in models]
        outputs = [process.communicate(timeout=SESSION_TIMEOUT_SECONDS) for process in processes]
    record.write_text("".join(path.read_text(encoding="utf-8") for path in records if path.exists()),
                      encoding="utf-8")
    # Report the first session that did not finish its script, if any.
    worst = next((index for index, (stdout, _) in enumerate(outputs) if not _completed(stdout)), 0)
    return subprocess.CompletedProcess(processes[worst].args, processes[worst].returncode, *outputs[worst])


def _mcp_arguments(record_dir: Path) -> list:
    server = Path(__file__).with_name("mcp_fixture.py")
    config = record_dir / "mcp-config.json"
    config.write_text(json.dumps({"mcpServers": {"fixture": {
        "command": Path(sys.executable).as_posix(), "args": [server.as_posix()]}}}), encoding="utf-8")
    return ["--mcp-config", str(config), "--strict-mcp-config"]


def _reduced_reported(journal: Path, start: int) -> bool:
    """Whether the hook recorded a reduced-detection summary during this scenario."""
    if not journal.exists():
        return False
    with journal.open("rb") as stream:
        stream.seek(start)
        rows = [json.loads(line) for line in stream.read().decode("utf-8").splitlines() if line.strip()]
    return any(row.get("reduced") for row in rows)


def _completed(stdout: bytes) -> bool:
    try:
        return json.loads(stdout).get("result") == FINAL_TEXT
    except (ValueError, AttributeError):
        return False


def _count_lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())
