# Model-boundary checks — 2026-10-07

First observation of what a real Claude Code session sends to the model with
Privacy Guard installed. This addresses part of SEC-01 and SEC-03; it does not
close either. Receipts keep canary ids only.

## Method

`tools/check_model_boundary.py` installs the TEST-IDENTITY setup into an isolated
profile (`USERPROFILE`, `HOME` and `CLAUDE_CONFIG_DIR` redirected), then runs
scripted headless sessions (`claude -p`) against a local fake Messages API
(`ANTHROPIC_BASE_URL`). The fake API records every request body and dictates the
tool calls; no request leaves the machine. A scenario fails when any of eight
synthetic canaries (three names, two e-mails, a phone number, an IBAN and a
GitHub token) appears in a recorded request.

```
python tools/check_model_boundary.py dist/PrivacyGuard-Test-<version>-windows-x64.exe --work <short new dir>
```

| Item | Value |
| --- | --- |
| Claude Code | 2.1.280, native Windows, sessions with `--dangerously-skip-permissions` in a throwaway workspace |
| Setup | `PrivacyGuard-Test-0.1.0-preview.1-windows-x64.exe` (receipt of 2026-10-07) |
| Windows | 11 Home x64, build 10.0.26200; maintainer machine, not a clean VM |
| Detection mode | Bundled DistilCamemBERT + INSEE index, loaded by the setup |

## Results

| Scenario | Hook | Observed at the model boundary | Verdict |
| --- | --- | --- | --- |
| control-unprotected-read | none | 6 canaries | expected (harness sensitivity) |
| read-csv | installed | tokens only | pass |
| bash-cat (`cat customers.csv`) | installed | tokens only | pass |
| parallel-reads (two `Read` in one turn) | installed | tokens only | pass |
| secret-env (`Read .env`) | installed | `⟦GITHUB_TOKEN:REDACTED⟧` | pass |
| write-restore-reread | installed | tokens only; originals restored on disk | pass |
| grep-content (`Grep`, content mode) | installed | name-1, name-2, name-3 | **fail** |
| bash-failure (`cat notes.md; exit 3`) | installed | name-3, email-2 | **fail** |
| hook-timeout (3 s limit, hook sleeps) | faulted | 6 canaries | leak, platform limit |
| hook-launch-error (missing runtime) | faulted | 6 canaries | leak |

`grep-content`, `bash-failure`, `secret-env` and `write-restore-reread` were
run twice in fresh profiles with identical outcomes.

## Findings

1. **Failed-tool stop is not enforced.** On `PostToolUseFailure`, the hook
   detected the values (`failures.jsonl`: `sensitive_result`) and returned
   `continue: false`. Claude Code still sent the original error text in the next
   model request and completed the session. The fallback in
   `claude_code/failed_tool.py` does not prevent disclosure in this version.
2. **Grep output skips name detection.** `document_scope.is_document_read`
   reserves the name model for `Read` and shell commands naming a document file.
   `Grep` over the same CSV and Markdown files releases names; e-mail, phone and
   IBAN detectors still apply.
3. **A hook that times out or cannot start releases originals.** This turns the
   source-based concern in the baseline into an observed outcome. Catching errors
   inside the handler cannot cover it.

## Installation observations

- Installing under a long directory failed: a bundled `runtime/Doc/html/_downloads/...`
  path reached 264 characters with `LongPathsEnabled=0`. The default
  `%LOCALAPPDATA%\Programs\PrivacyGuard` is short enough; the Python
  documentation is not needed at runtime.
- Setup refused to install with about 1 GB of free memory ("The bundled name
  detector could not run on this computer") and rolled back cleanly. It
  succeeded with 2.6 GB free.
- Each failed or completed run left no uninstall registry entry.

## Not covered yet

Subagents, MCP results, Edit, Glob, binary or image results, resumed and compacted
history, concurrent sessions, competing transformations, and interactive VS Code or
terminal sessions. A fake API cannot show what Anthropic's servers would do; it
shows exactly what the agent sends. One run of the full unit suite reported a
single failure that did not reproduce in five further runs; it remains unidentified.

## Fixes measured with the source engine

Same harness with `--source` (this checkout replaces both engine copies of the
setup: the hook's `~/.privacy-guard/app` and the bundle's `app`, which the name
service imports through `python314._pth`). Claude Code 2.1.292, the version of the
VS Code extension, with `CLAUDE_CODE_USE_POWERSHELL_TOOL=1`: PowerShell is on by
default for claude.ai accounts on Windows and is then the primary shell.

| Scenario | Before | After | Change |
| --- | --- | --- | --- |
| grep-content | 3 names | tokens only | Grep content lines and targets count as document reads |
| bash-failure-status, bash-failure-grep | — | tokens only | `shell_failures`: a failing command ends with status 0, so PostToolUse masks it |
| powershell-get-content, powershell-notes | — | tokens only | PowerShell commands naming a document use the name model |
| powershell-failure | name, e-mail | tokens only | PowerShell trailer `Write-Output ''` |
| bash-cp1252 | whole output masked, session stopped | tokens only | Name model accepts lone surrogates and skipped symbols |
| bash-failure-exit | name, e-mail | unchanged | Residual: `exit` ends the shell before the trailer |
| hook-timeout, hook-launch-error | all canaries | unchanged | Residual: outside the hook's control |

Shell trailers were chosen by probing Claude Code's permission analysis on the
rewritten command: `trap`, `$?`, subshells and `if` blocks turn every command into
an approval prompt; the chosen trailers keep allow rules, read-only auto-approval
and denials (`rm`, `Remove-Item`, `curl`, `Invoke-WebRequest`) unchanged.

Other observations:

- `continue: false` is honoured after PostToolUse but ignored after PostToolUseFailure.
- Grep and Glob results gained fields in 2.1.292 (`totalLines`, `numMatches`,
  `truncated`...); the masked fallback now keeps unknown numbers and booleans and
  still refuses unknown text.
- A `�` replacing an accented letter can make the name model extend a name over the
  next word (over-masking, safe side).
- Detection benchmark (`--spaced`, DistilCamemBERT): identical before and after,
  names 33/35, every other category 100%, no false alarm.
