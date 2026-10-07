"""Mask recognized result schemas and stop processing after inspection errors.

Unknown shapes receive no speculative replacement. The universal stop remains
necessary: a post-tool error exit code alone cannot prevent model disclosure.
"""

from privacy_guard.claude_code.responses import HookResult, POST_TOOL_USE, stop

FAILURE_MESSAGE = "Privacy Guard : inspection impossible, traitement interrompu."
MASKED = "[Privacy Guard: Output masked; inspection failed.]"


def inspection_failed(event: str, payload: object) -> HookResult:
    fields = {}
    if event == POST_TOOL_USE and isinstance(payload, dict):
        try:
            replacement = masked_result(payload.get("tool_name"), payload.get("tool_response"))
        except Exception:
            replacement = None  # A malformed result must not break the stop response.
        if replacement is not None:
            fields["hookSpecificOutput"] = {"hookEventName": event, "updatedToolOutput": replacement}
    return stop(FAILURE_MESSAGE, **fields)


def masked_result(tool: object, original: object) -> object:
    if tool == "Bash":
        # The documented Bash output schema; never copy original stdout/stderr.
        return {"stdout": MASKED, "stderr": "", "interrupted": False, "isImage": False}
    if not isinstance(tool, str):
        return None
    if tool.startswith("mcp__"):
        return {"content": [{"type": "text", "text": MASKED}], "isError": True}
    if not isinstance(original, dict):
        return None
    if tool == "Read":
        if set(original) == {"content"} and isinstance(original["content"], str):
            return {"content": MASKED}  # Legacy/test adapter's text envelope.
        if (set(original) == {"type", "file"} and original["type"] == "text"
                and isinstance(original["file"], dict)):
            file = original["file"]
            if (set(file) == {"filePath", "content", "numLines", "startLine", "totalLines"}
                    and isinstance(file["filePath"], str)
                    and isinstance(file.get("content"), str)
                    and all(type(v) is int for k, v in file.items() if k not in {"content", "filePath"})):
                return {"type": "text", "file": {
                    k: MASKED if k == "content" else "[masked]" if k == "filePath" else v
                    for k, v in file.items()}}
    if tool in {"Grep", "Glob"}:
        allowed = {"mode", "content", "filenames", "numFiles", "numLines", "durationMs", "appliedLimit", "appliedOffset"}
        if (set(original) <= allowed and isinstance(original.get("filenames"), list)
                and ("mode" not in original or isinstance(original["mode"], str)
                     and original["mode"] in {"content", "files_with_matches", "count"})
                and all(type(v) is int for k, v in original.items() if k not in {"mode", "content", "filenames"})
                and ("content" not in original or isinstance(original["content"], str))):
            return {k: [] if k == "filenames" else MASKED if k == "content" else v
                    for k, v in original.items()}
    return None
