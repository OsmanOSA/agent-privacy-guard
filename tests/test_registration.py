import unittest

from privacy_guard.claude_code import registration

COMMAND = '"python" "/home/user/.privacy-guard/app"'
USER_HOOK = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo user"}]}


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
