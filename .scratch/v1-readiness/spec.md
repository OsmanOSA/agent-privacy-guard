# V1 readiness: from preview to a distributable setup

Status: open

## Problem

The model-boundary campaign of 2026-10-07 (`docs/security/boundary-checks-2026-10-07.md`)
protects 12 of 13 covered scenarios with the source engine on Claude Code 2.1.292.
The V1 is still not distributable: three leaks remain, false positives blind the agent,
common configurations are untested and the built setup predates the fixes.

## Outcome

A rebuilt TEST-IDENTITY setup passes the full boundary campaign, then goes to two or
three trusted testers as a preview. Public distribution additionally needs item 09.

## Rule for every item

Measure before and after with `tools/check_model_boundary.py --source` on the Claude
Code version users run (VS Code extension binary, PowerShell tool enabled). Detection
changes also run `python -m benchmark --spaced`: recall and precision must not drop.
Get the unit suite green before any redeploy.

## Work items, in order

| ID | Item | Priority | Status |
| --- | --- | --- | --- |
| 01 | [Tool names taken for person names](issues/01-tool-name-false-positives.md) | P0 usability | done |
| 02 | [Hook command without Git Bash](issues/02-hook-without-git-bash.md) | P0 leak | done |
| 03 | [Explicit exit in a shell command](issues/03-explicit-exit.md) | P0 leak | done |
| 04 | [Hook timeout](issues/04-hook-timeout.md) | P0 leak | done |
| 05 | [Hook launch failure](issues/05-hook-launch-failure.md) | P0 leak | open |
| 06 | [Silent degradation without the name model](issues/06-silent-degradation.md) | P0 leak | open |
| 07 | [Rebuild and harden the setup](issues/07-rebuild-setup.md) | P1 | open |
| 08 | [Untested paths](issues/08-untested-paths.md) | P1 | open |
| 09 | [Public distribution prerequisites](issues/09-public-distribution.md) | P2 | open |
| 11 | [Hook refusals disclose the local user path](issues/11-refusal-path-disclosure.md) | P1 | open |
| 10 | [End-of-work summary notification](issues/10-end-of-work-summary.md) | later | blocked |

## Already fixed (branch `fix/model-boundary-leaks`, commit 8018c89)

Failing Bash and PowerShell commands, Grep content, PowerShell document reads,
undecodable bytes in the name model, new Grep/Glob result fields.

## Out of scope

A local API gateway and any native UI: the product stays an invisible hook layer whose
only visible surface is its notifications.
