import unittest

from privacy_guard.claude_code import registration

PYTHON, APP = "C:/runtime/python.exe", "C:/Users/u/.privacy-guard/app"
COMMAND = registration.hook_handlers(PYTHON, APP)
# Shell-string entry written by 0.1.0-preview.1.
LEGACY = {"type": "command", "command": '"python" "/home/user/.privacy-guard/app"', "timeout": 30}
USER_HOOK = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo user"}]}


class HookHandlersTest(unittest.TestCase):
    def test_events_after_the_tool_use_exec_form_without_shell(self):
        for event in ("PostToolUse", "PostToolUseFailure", "SessionStart", "SessionEnd"):
            with self.subTest(event=event):
                self.assertEqual(COMMAND[event], {"type": "command", "command": PYTHON, "args": [APP],
                                                  "timeout": registration.HOOK_TIMEOUT_SECONDS})

    def test_pre_tool_use_guard_blocks_when_the_runtime_cannot_run(self):
        guard = COMMAND["PreToolUse"]
        self.assertEqual(guard["shell"], "powershell")
        self.assertIn(f"& '{PYTHON}' '{APP}'", guard["command"])
        self.assertIn("exit 2", guard["command"])

    def test_guard_quotes_paths_literally(self):
        guard = registration.guard_handler("C:/Users/O'Brien $x/python.exe", APP)
        self.assertIn("'C:/Users/O''Brien $x/python.exe'", guard["command"])

    def test_legacy_string_entries_are_replaced_on_upgrade(self):
        legacy = {"hooks": {event: [{"matcher": "*", "hooks": [LEGACY]}] for event in registration.HOOK_EVENTS}}
        upgraded = registration.register(legacy, COMMAND)
        self.assertEqual(registration.owned_targets(upgraded),
                         {(PYTHON, (APP,)), (COMMAND["PreToolUse"]["command"], ())})
        self.assertEqual(registration.unregister(legacy), {})

    def test_owned_targets_ignore_user_hooks(self):
        settings = registration.register({"hooks": {"PreToolUse": [USER_HOOK]}}, COMMAND)
        self.assertEqual(len(registration.owned_targets(settings)), 2)


class RegisterTest(unittest.TestCase):
    def test_registers_on_every_event(self):
        settings = registration.register({}, COMMAND)

        self.assertEqual(registration.registered_events(settings), {event: True for event in registration.HOOK_EVENTS})

    def test_keeps_unrelated_settings_and_user_hooks(self):
        original = {"model": "opus", "hooks": {"PreToolUse": [USER_HOOK]}}

        settings = registration.register(original, COMMAND)

        self.assertEqual(settings["model"], "opus")
        self.assertIn(USER_HOOK, settings["hooks"]["PreToolUse"])

    def test_is_idempotent(self):
        once = registration.register({}, COMMAND)

        twice = registration.register(once, COMMAND)

        self.assertEqual(once, twice)

    def test_does_not_mutate_input(self):
        original = {"hooks": {"PreToolUse": [USER_HOOK]}}

        registration.register(original, COMMAND)

        self.assertEqual(original, {"hooks": {"PreToolUse": [USER_HOOK]}})


class UnregisterTest(unittest.TestCase):
    def test_restores_original_settings(self):
        original = {"model": "opus", "hooks": {"PreToolUse": [USER_HOOK]}}

        restored = registration.unregister(registration.register(original, COMMAND))

        self.assertEqual(restored, original)

    def test_removes_hooks_key_when_nothing_left(self):
        restored = registration.unregister(registration.register({}, COMMAND))

        self.assertEqual(restored, {})


if __name__ == "__main__":
    unittest.main()
