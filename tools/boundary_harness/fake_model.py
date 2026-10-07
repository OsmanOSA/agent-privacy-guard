"""Scripted stand-in for the Anthropic Messages API that records the model boundary.

Claude Code is pointed at it through ANTHROPIC_BASE_URL. Every request body is
appended to a JSONL file: that file is exactly what the agent sent to "the model".
Replies follow a script of tool calls, so a real agent session runs offline and
deterministically, with synthetic data only.

Interface:
    with FakeModel(script, record_path) as model:
        model.base_url            # value for ANTHROPIC_BASE_URL
    script: list of steps. A step is a list of (tool_name, tool_input) calls issued
    in one assistant turn, or a callable(messages) returning that list.

Progress is read back from tool_use ids, which encode their step: Claude Code may
merge assistant turns or append system messages, so counting messages is unreliable.
"""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FINAL_TEXT = "Scripted session finished."
STEP_ID = re.compile(r"^toolu_s(\d+)_")
USAGE = {"input_tokens": 1, "output_tokens": 1,
         "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}


def next_step(script: list, body: dict) -> tuple[int, list]:
    """Index and calls of the agent's next scripted turn; no calls once finished.

    Requests without the scripted tools (titles, summaries...) are side requests
    and get plain text, so they never advance the script.
    """
    names = {tool.get("name") for tool in body.get("tools") or ()}
    messages = body.get("messages") or []
    wanted = {name for step in script if not callable(step) for name, _ in step}
    if not names or not wanted <= names:
        return -1, []
    done = len({match.group(1) for match in map(STEP_ID.match, _tool_use_ids(messages)) if match})
    if done >= len(script):
        return done, []
    step = script[done]
    return done, step(messages) if callable(step) else step


def assistant_blocks(calls: list, step: int) -> list:
    """Message content for the scripted calls, or the final text when none remain."""
    if not calls:
        return [{"type": "text", "text": FINAL_TEXT}]
    return [{"type": "tool_use", "id": f"toolu_s{step:02d}_{index:02d}", "name": name, "input": arguments}
            for index, (name, arguments) in enumerate(calls)]


def stream_events(model: str, blocks: list) -> list:
    """Server-sent events equivalent to one complete message."""
    stop = "tool_use" if blocks[0]["type"] == "tool_use" else "end_turn"
    events = [("message_start", {"type": "message_start", "message": {
        "id": "msg_fake", "type": "message", "role": "assistant", "model": model,
        "content": [], "stop_reason": None, "stop_sequence": None, "usage": USAGE}})]
    for index, block in enumerate(blocks):
        if block["type"] == "tool_use":
            start = dict(block, input={})
            delta = {"type": "input_json_delta", "partial_json": json.dumps(block["input"])}
        else:
            start = {"type": "text", "text": ""}
            delta = {"type": "text_delta", "text": block["text"]}
        events += [("content_block_start", {"type": "content_block_start", "index": index, "content_block": start}),
                   ("content_block_delta", {"type": "content_block_delta", "index": index, "delta": delta}),
                   ("content_block_stop", {"type": "content_block_stop", "index": index})]
    events += [("message_delta", {"type": "message_delta", "usage": {"output_tokens": 1},
                                  "delta": {"stop_reason": stop, "stop_sequence": None}}),
               ("message_stop", {"type": "message_stop"})]
    return events


def _tool_use_ids(messages: list) -> list:
    return [block.get("id", "") for message in messages if message.get("role") == "assistant"
            and isinstance(message.get("content"), list)
            for block in message["content"] if block.get("type") == "tool_use"]


class FakeModel:
    """Local HTTP server answering Messages API calls from a script."""

    def __init__(self, script: list, record_path: Path):
        self._script = script
        self._record = record_path
        self._lock = threading.Lock()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def __enter__(self) -> "FakeModel":
        self._thread.start()
        return self

    def __exit__(self, *_) -> None:
        self._server.shutdown()
        self._server.server_close()

    def _save(self, path: str, body: dict) -> None:
        with self._lock, self._record.open("a", encoding="utf-8") as record:
            record.write(json.dumps({"path": path, "body": body}, ensure_ascii=False) + "\n")

    def _handler(self):
        model = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                model._save(self.path, body)
                if "count_tokens" in self.path:
                    return self._json({"input_tokens": 1})
                step, calls = next_step(model._script, body)
                blocks = assistant_blocks(calls, step)
                if body.get("stream"):
                    return self._stream(stream_events(body.get("model", "fake"), blocks))
                stop = "tool_use" if blocks[0]["type"] == "tool_use" else "end_turn"
                return self._json({"id": "msg_fake", "type": "message", "role": "assistant",
                                   "model": body.get("model", "fake"), "content": blocks,
                                   "stop_reason": stop, "stop_sequence": None, "usage": USAGE})

            def do_GET(self):
                self._json({"data": [], "has_more": False})

            def do_HEAD(self):
                self.send_response(200)
                self.end_headers()

            def _json(self, payload):
                data = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _stream(self, events):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                for name, data in events:
                    self.wfile.write(f"event: {name}\ndata: {json.dumps(data)}\n\n".encode())
                self.wfile.flush()
                self.close_connection = True

            def log_message(self, *_):
                pass  # Request lines carry no secrets, but the console is not evidence.

        return Handler
