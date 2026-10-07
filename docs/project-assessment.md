# Project assessment and next steps

Assessment date: 2026-10-05. Source reviewed: `8dfe62f`. This document records a maintainer-facing assessment and proposed priorities. It does not certify protection or approve an architectural change.

Agent Privacy Guard has a local detection core, reversible session mappings, native encryption and a testable adapter. The next experiment should check whether a real agent can read and edit a document while detected personal values stay out of model context, including when inspection fails. If the integration cannot enforce that behavior, its interception mechanism needs to change.

## Why the project deserves further work

The problem is specific: an agent can encounter customer data or credentials while reading a file or running a command for a legitimate task. A developer may need the agent to understand the structure and relationships in that data without receiving every original value. The proposed workflow keeps substitutes consistent during reasoning and restores approved values in a local output.

Detection, the vault, operating-system encryption and agent protocol handling have separate modules. The tests exercise those interfaces with synthetic data. A contributor can investigate one missed value or one tool-response failure without rebuilding the application.

[Presidio](https://presidio.dataprivacystack.org/) already documents detection, transformation and pseudonymization with mappings. For this agent integration, we still need to demonstrate which paths are covered, whether the agent can complete its task, where restoration is allowed and how users learn that protection is unavailable. No customer demand or willingness to pay has been measured.

## What exists today

| Area | Evidence available | Practical limit |
| --- | --- | --- |
| Source distribution | Published GitHub repository, MIT license, reviewed three-commit history | Source publication is not a product release or a security certification |
| Local core | Detection rules, session tokens, encrypted mappings and restoration code | Unknown data and representations can be missed |
| Adapter | Claude Code hooks and install/status/uninstall commands | No recorded observation of actual model requests |
| Windows checks | 125 tests run with Git Bash: 124 passed, one optional-model test skipped | The default shell selection can still choose WSL Bash and fail to launch native Python |
| Detection benchmark | Heuristic run: seven secret occurrences found; 19 of 35 name occurrences found | Small synthetic corpus; 54% name recall; no model-enabled quality result from this run |
| Documentation | Product scope, threat model, local security backlog and proposed UX | The documented target extends beyond demonstrated behavior |

The [original baseline](security/baseline-2026-10-05.md) retains its earlier three shell-launch failures. The later passing run selected Git Bash explicitly; it does not show that automatic shell discovery has been fixed. Publication and scanning evidence is recorded in the [history audit](security/history-audit-2026-10-05.md).

The optional local ONNX name service exists in the source. Its presence does not justify applying a model-enabled detection score to a heuristic benchmark.

## The technical questions that decide the project

### Does replacement survive a real failure

`hook.fail_closed` currently returns a plain string after a post-tool error. The [Claude Code hook contract](https://code.claude.com/docs/en/hooks#posttooluse-decision-control) says an invalid built-in replacement is ignored and the original result is used. Our source and that contract therefore point to a possible disclosure during the error path. This is a source-based finding, not a reproduced real-agent incident.

The [timeout contract](https://code.claude.com/docs/en/hooks#timeouts) also lets a timed-out command hook on `PreToolUse` continue through ordinary permissions. Catching exceptions inside our Python handler cannot control that external behavior. See SEC-01 and SEC-03 in the [backlog](../.scratch/security-baseline/spec.md).

### Can restoration be restricted to an approved operation

`restore_tool_input` permits restoration based on the tool name, including Bash. `PrivacyCore.restore` does not know the destination. A command can receive an original value and then transmit it, or treat part of that value as executable syntax. Local execution alone does not establish an approved destination.

My recommendation for the first trial is to exclude credentials from automatic restoration and permit personal-value restoration only through a constrained local data writer. That writer needs an approved output root, a supported data format and explicit operation checks. This is a proposed policy for SEC-02, not existing behavior.

### Can users tell what is actually covered

The adapter currently maps nested string values in selected events. Dictionary keys, binary content and other paths do not gain protection from that transformation. Installation status does not prove that the current session is covered.

The [Claude Code sandbox](https://code.claude.com/docs/en/sandboxing) supplies filesystem and network restrictions for shell execution on supported systems. It excludes file tools, MCP servers and hooks, and is unavailable on native Windows. It cannot simply be counted as enforcement for this native Windows prototype. The choice of enforcement mechanism remains open.

## The first workflow I would validate

Use one pinned Claude Code version, one native Windows environment and one declared shell. Ask the agent to read a synthetic customer CSV, check its structure and produce an edited local CSV. Names and contact values should stay represented by consistent tokens during reasoning. Only an approved local export should recover the originals. A synthetic API credential in the input should remain masked.

This scenario tests both what the agent receives and what it writes locally, including failures that a detector-only test would miss. CSV text avoids adding OCR or binary document extraction before the agent contract is understood.

Observe the model-request boundary with a controlled harness, using synthetic values only. Check the successful read, a detection exception, an invalid replacement, a missing or killed hook, a timeout, a failed tool and competing transformations. Check attempts to restore into a network command, an unapproved path or another session. Retain fixture identifiers, environment versions and outcomes as evidence.

If a path still sends originals under the claimed failure policy, stop calling it covered. Evaluate another interception point or a more constrained execution flow before expanding the feature list.

## Work in order

1. **Prove one path through the real agent.** Build the boundary harness and record success and failure behavior for the chosen workflow. Deliver a compatibility receipt, including cases that cannot be enforced. This is the next implementation priority.
2. **Constrain restoration and explain reduced capability.** Implement the approved destination policy, show model absence and hook failure clearly, and measure detection separately from interception. Continue only when the covered workflow has evidence for both useful output and denied disclosure attempts.
3. **Run a small external trial.** After the security gates, use the product brief's proposed cohort: interview ten developers about actual tasks they avoid, invite five to run a synthetic trial, and observe whether at least three choose to continue after a week. These are discovery targets, not achieved results or proof of a market.

During a trial, record installation time, latency, blocked legitimate tasks, restoration errors, known misses and support effort. Compare the workflow with manual sanitization and an existing detector under equivalent conditions. Do not replace those observations with a single aggregate security score.

More agents, more operating systems, a desktop application and commercial packaging can follow evidence from that sequence. The existing [roadmap](roadmap.md) retains their release gates. A second adapter should follow a demonstrated first adapter.

## When to continue or change direction

Continue if the boundary checks confirm the declared failure behavior and trial users complete work they otherwise avoid. Assess willingness to pay separately from continued use.

Change the integration mechanism if the agent contract cannot enforce the promised boundary. Narrow the use case if detection or setup prevents useful work. Reconsider commercial packaging if maintenance effort exceeds what trial users value.
