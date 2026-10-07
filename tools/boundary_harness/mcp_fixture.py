"""Minimal stdio MCP server returning synthetic customer data, for boundary scenarios.

Two tools: `customer_card` answers with canaries; `customer_lookup_error` fails
(`isError`) with canaries in its error text, the MCP equivalent of a failing command.

Run by Claude Code through `--mcp-config`; speaks newline-delimited JSON-RPC 2.0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from boundary_harness.scenarios import CANARIES  # noqa: E402

TOOLS = {
    "customer_card": (False, f"Client : {CANARIES['name-1']}, {CANARIES['email-1']}, {CANARIES['phone-1']}"),
    "customer_lookup_error": (True, f"Lookup failed for {CANARIES['name-3']} <{CANARIES['email-2']}>"),
}


def answer(request: dict) -> dict | None:
    method, identifier = request.get("method"), request.get("id")
    if identifier is None:
        return None  # Notifications such as notifications/initialized need no answer.
    if method == "initialize":
        result = {"protocolVersion": request["params"].get("protocolVersion", "2025-06-18"),
                  "capabilities": {"tools": {}}, "serverInfo": {"name": "fixture", "version": "1"}}
    elif method == "tools/list":
        result = {"tools": [{"name": name, "description": "Synthetic customer data.",
                             "inputSchema": {"type": "object", "properties": {}}} for name in TOOLS]}
    elif method == "tools/call":
        is_error, text = TOOLS[request["params"]["name"]]
        result = {"content": [{"type": "text", "text": text}], "isError": is_error}
    else:
        result = {}
    return {"jsonrpc": "2.0", "id": identifier, "result": result}


def main() -> None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        if line.strip():
            reply = answer(json.loads(line))
            if reply is not None:
                sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    main()
