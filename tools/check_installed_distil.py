"""Exercise the installed native hook on synthetic cycles and a published excerpt."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT / "evaluation/ner/distil-installed-check-20261006.json")
    parser.add_argument("--restart-service", action="store_true")
    args = parser.parse_args()
    guard = (Path.home() / ".privacy-guard").resolve()
    assert guard == Path.home().resolve() / ".privacy-guard"
    session = "distil-probe-" + uuid.uuid4().hex
    session_dir = (guard / "vault" / session).resolve()
    assert session_dir.is_relative_to(guard / "vault") and session_dir.name == session
    # Exec form, as registered: Claude Code starts the interpreter without a shell.
    command = [Path(sys.executable).as_posix(), (guard / "app").as_posix()]
    settings = json.loads((Path.home() / ".claude/settings.json").read_text(encoding="utf-8"))
    for event in ("PostToolUse", "PostToolUseFailure"):
        assert any([h.get("command"), *(h.get("args") or [])] == command
                   for g in settings["hooks"][event] for h in g["hooks"]), f"{event} hook not registered"
    if args.restart_service:
        sys.path.insert(0, str(PROJECT))
        from privacy_guard.service.channel import ServiceChannel
        from privacy_guard.service.client import ServiceClient

        ServiceClient(ServiceChannel(guard / "run")).stop()

    notices = []

    def call(event, tool=None, arguments=None, response=None, error=None, session_id=None):
        payload = {"hook_event_name": event, "session_id": session_id or session}
        if tool:
            payload.update(tool_name=tool, tool_input=arguments or {}, tool_response=response)
        if error is not None:
            payload["error"] = error
        started = time.perf_counter()
        completed = subprocess.run(command, input=json.dumps(payload),
                                   capture_output=True, text=True, encoding="utf-8", timeout=30)
        elapsed = (time.perf_counter() - started) * 1000
        assert completed.returncode == 0 and not completed.stderr, "Installed hook failed"
        reply = json.loads(completed.stdout) if completed.stdout else {}
        if "systemMessage" in reply:
            notices.append(reply["systemMessage"])
        return reply, elapsed

    def read(path, text):
        reply, elapsed = call("PostToolUse", "Read", {"file_path": str(path)}, {"content": text})
        return reply.get("hookSpecificOutput", {}).get("updatedToolOutput", {"content": text})["content"], elapsed

    try:
        call("SessionStart")
        with tempfile.TemporaryDirectory(prefix="distil-cycle-", dir=PROJECT / ".local-review") as directory:
            path = Path(directory) / "source.txt"
            original = "Jean Dupont a rencontré Sophie Lefèvre. Courriel : jean.dupont@example.com.\n"
            path.write_text(original, encoding="utf-8")
            masked, _ = read(path, original)
            assert all(value not in masked for value in ["Jean Dupont", "Sophie Lefèvre", "jean.dupont@example.com"])
            target = Path(directory) / "result.md"
            target.write_text(masked, encoding="utf-8")
            reply, _ = call("PostToolUse", "Write", {"file_path": str(target), "content": masked}, {"success": True})
            assert "personal values restored" in reply.get("hookSpecificOutput", {}).get("additionalContext", "")
            assert "restituées" in reply.get("systemMessage", "")
            restored = target.read_text(encoding="utf-8")
            assert restored == original
            reread, _ = read(target, restored)
            assert reread == masked
            code = "print('ready')\n" * 999 + "# Author: Jean Dupont\n"
            protected_code, code_ms = read(Path(directory) / "app.py", code)
            assert "Jean Dupont" not in protected_code
            reference = json.loads((PROJECT / "evaluation/ner/latency-length-20261006.json").read_text())
            source = PROJECT / "evaluation/ner/data/raw/additional-20261006/europeana.bio"
            assert hashlib.sha256(source.read_bytes()).hexdigest() == reference["source_sha256"]
            long_text = " ".join(line.rsplit(None, 1)[0] for line in source.read_text(encoding="utf-8").splitlines() if line.strip())
            case = reference["cases"][-1]
            long_text = long_text[:case["characters"]]
            assert hashlib.sha256(long_text.encode()).hexdigest() == case["text_sha256"]
            first, first_ms = read(path, long_text)
            second, reread_ms = read(path, long_text)
            assert first == second and "⟦PERSON_NAME:" in first
            failed, _ = call("PostToolUse", "Bash", response={"stdout": original, "stderr": ""},
                             session_id="invalid/session")
            assert failed["continue"] is False
            masked_failure = failed["hookSpecificOutput"]["updatedToolOutput"]
            assert set(masked_failure) == {"stdout", "stderr", "interrupted", "isImage"}
            assert "jean.dupont@example.com" not in json.dumps(failed)
            sensitive, _ = call("PostToolUseFailure", "Bash", error="Exit code 1: jean.dupont@example.com")
            assert sensitive["continue"] is False and "jean.dupont@example.com" not in json.dumps(sensitive)
            clean, _ = call("PostToolUseFailure", "Bash", error="Exit code 1: command unavailable")
            assert clean == {}
            summaries = [json.loads(line) for line in (guard / "logs/protection.jsonl").read_text(encoding="utf-8").splitlines()]
            sample = next(row for row in reversed(summaries) if row["document"] == "source.txt"
                          and row["pseudonymized"] == {"person_name": 2, "email": 1})
            assert set(sample) == {"timestamp", "document", "count_unit", "pseudonymized", "redacted"}
            assert all(value not in json.dumps(sample) for value in ("Jean Dupont", "Sophie Lefèvre", "jean.dupont@example.com", str(path.parent)))
            report = {"installed_native_git_bash_cycle": True, "local_restoration_exact": True,
                      "reread_tokens_stable": True, "python_lines": 1000, "python_read_ms": code_ms,
                      "published_excerpt_tokens": case["tokens"], "document_first_read_ms": first_ms,
                      "document_identical_reread_ms": reread_ms,
                      "native_user_notices_emitted": any("pseudonymis" in n for n in notices),
                      "native_notice_contains_counts": any("2 noms et 1 adresse e-mail" in n for n in notices),
                      "native_notice_contains_basename": any("source.txt" in n for n in notices),
                      "local_summary_journal_verified": True,
                      "native_stop_on_inspection_error": failed["continue"] is False,
                      "native_stop_on_sensitive_tool_failure": sensitive["continue"] is False,
                      "clean_tool_failure_continues": clean == {},
                      "visual_notification_display_verified": False,
                      "scope": "Installed hook subprocess and real service; no Claude model-network observation"}
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report, indent=2))
    finally:
        # Remove only this probe's own vault. SessionEnd would also purge old user vaults.
        if session_dir.exists():
            shutil.rmtree(session_dir)


if __name__ == "__main__":
    main()
