"""Protect tool results; local file restoration is handled separately after Write."""

from __future__ import annotations

from collections import Counter

from typing import Callable

from privacy_guard.claude_code.read_guidance import guide_document_read
from privacy_guard.claude_code.notices import notify
from privacy_guard.claude_code.responses import HookResult, allow, replace_tool_output
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.protection_summary import ProtectionSummary
from privacy_guard.diagnostics import stage


def protect_tool_output(payload: dict,
                        core: PrivacyCore, report: Callable[[ProtectionSummary], None] | None = None) -> HookResult:
    """Protect text values in a tool result, keeping its structure."""
    output = payload.get("tool_response")
    counts = Counter()
    texts = []

    def collect(text):
        texts.append(text)
        return text

    with stage('output_mapping'):
        map_strings(output, collect)
    prepared = iter(core.protect_many_with_counts(texts))

    def protect(text):
        protected, found = next(prepared)
        counts.update(found)
        return protected

    with stage('output_mapping'):
        protected = map_strings(output, protect)

    result = allow()
    if protected != output:
        arguments = payload.get("tool_input")
        document = (arguments.get("file_path") if isinstance(arguments, dict)
                    and payload.get("tool_name") in {"Read", "Write", "Edit"} else None)
        summary = ProtectionSummary(dict(counts), document)
        if report is not None:
            with stage('protection_journal'):
                report(summary)
        with stage('output_response'):
            result = notify(replace_tool_output(protected), summary.message())

    return guide_document_read(payload, protected, result)


def map_strings(value: object,
                transform: Callable[[str], str]) -> object:
    """Apply a transformation to nested JSON string values, preserving structure."""
    if isinstance(value, str):
        return transform(value)
    if isinstance(value, list):
        return [map_strings(item, transform) for item in value]
    if isinstance(value, dict):
        return {key: map_strings(item, transform) for key, item in value.items()}
    return value
