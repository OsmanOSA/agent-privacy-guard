import json
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

# The harness lives with the other maintainer tools, outside the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from boundary_harness.fake_model import FINAL_TEXT, MAIN, FakeModel, next_step, stream_events  # noqa: E402
from boundary_harness.session import leaked_ids, observed_strings  # noqa: E402
from boundary_harness.scenarios import CANARIES  # noqa: E402

READ = ("Read", {"file_path": "a.csv"})
TOOLS = [{"name": "Read"}, {"name": "Bash"}]


def tool_turn(step):
    return {"role": "assistant", "content": [{"type": "tool_use", "id": f"toolu_s{step:02d}_00", "name": "Read", "input": {}}]}


class NextStepTest(unittest.TestCase):
    def test_script_advances_once_per_answered_tool_turn(self):
        script = [[READ], [("Bash", {"command": "ls"})]]
        body = {"tools": TOOLS, "messages": [{"role": "user", "content": "go"}]}
        self.assertEqual(next_step(script, body), (0, [READ]))
        body["messages"] += [tool_turn(0), {"role": "user", "content": []}]
        self.assertEqual(next_step(script, body)[1][0][0], "Bash")
        body["messages"] += [tool_turn(1), {"role": "system", "content": "reminder"}]
        self.assertEqual(next_step(script, body), (2, []))

    def test_merged_assistant_turns_still_count_each_step(self):
        merged = {"role": "assistant", "content": tool_turn(0)["content"] + tool_turn(1)["content"]}
        body = {"tools": TOOLS, "messages": [merged]}
        self.assertEqual(next_step([[READ], [READ], [READ]], body), (2, [READ]))

    def test_subagent_conversation_follows_its_own_script(self):
        script = {MAIN: [[("Agent", {"prompt": "SUBAGENT-TASK read"})]], "SUBAGENT-TASK": [[READ]]}
        tools = TOOLS + [{"name": "Agent"}]
        sub = {"tools": tools, "messages": [{"role": "user", "content": [{"type": "text", "text": "SUBAGENT-TASK read"}]}]}
        main = {"tools": tools, "messages": [{"role": "user", "content": "go"}]}
        self.assertEqual(next_step(script, sub), (0, [READ]))
        self.assertEqual(next_step(script, main)[1][0][0], "Agent")

    def test_side_request_without_scripted_tools_gets_text(self):
        self.assertEqual(next_step([[READ]], {"messages": [{"role": "user", "content": "title"}]}), (-1, []))

    def test_callable_step_receives_the_conversation(self):
        script = [lambda messages: [("Read", {"file_path": str(len(messages))})]]
        self.assertEqual(next_step(script, {"tools": TOOLS, "messages": [{}, {}]}),
                         (0, [("Read", {"file_path": "2"})]))

    def test_stream_carries_tool_input_as_json_delta(self):
        events = stream_events("m", [{"type": "tool_use", "id": "t", "name": "Read", "input": {"x": 1}}])
        deltas = [data["delta"] for name, data in events if name == "content_block_delta"]
        self.assertEqual(json.loads(deltas[0]["partial_json"]), {"x": 1})
        self.assertEqual(events[-2][1]["delta"]["stop_reason"], "tool_use")


class FakeModelServerTest(unittest.TestCase):
    def test_records_every_body_and_answers_final_text(self):
        with tempfile.TemporaryDirectory() as temp:
            record = Path(temp) / "record.jsonl"
            body = {"model": "m", "messages": [{"role": "user", "content": CANARIES["email-1"]}]}
            with FakeModel([[READ]], record) as model:
                request = urllib.request.Request(model.base_url + "/v1/messages",
                                                 data=json.dumps(body).encode(), method="POST")
                with urllib.request.urlopen(request) as response:
                    reply = json.loads(response.read())
            self.assertEqual(reply["content"][0]["text"], FINAL_TEXT)
            self.assertEqual(leaked_ids(observed_strings(record)), ["email-1"])


if __name__ == "__main__":
    unittest.main()
