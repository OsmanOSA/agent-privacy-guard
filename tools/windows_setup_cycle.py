"""Synthetic hook cycle using only the installed Windows runtime."""

import json
import subprocess


def exercise(python, profile, env):
    guard = profile / '.privacy-guard'
    # Avoid displaying test notifications while exercising the real hook.
    preferences = guard / 'notifications/settings.json'
    assert json.loads(preferences.read_text())['mode'] == 'background'
    preferences.write_text('{"version":1,"mode":"off","style":"card"}')

    def call(payload):
        result = subprocess.run([str(python), str(guard / 'app')],
                                input=json.dumps({'session_id': 'setup-cycle', **payload}),
                                capture_output=True, text=True, encoding='utf-8', env=env, timeout=40)
        assert result.returncode == 0, result.stderr
        response = json.loads(result.stdout) if result.stdout else {}
        assert response.get('continue', True), 'Installed hook requested a stop'
        return response.get('hookSpecificOutput', {})

    def read(text, path):
        return call({'hook_event_name': 'PostToolUse', 'tool_name': 'Read',
                     'tool_input': {'file_path': str(path)},
                     'tool_response': {'content': text}})['updatedToolOutput']['content']

    source = 'Madame Sophie Martin habite Paris. Contact : sophie.martin@example.com'
    target = profile / 'summary.md'
    protected = read(source, target)
    assert 'Sophie Martin' not in protected and 'sophie.martin@example.com' not in protected
    assert 'PERSON_NAME:' in protected and 'EMAIL:' in protected
    assert read(source, target) == protected
    assert 'DistilCamemBERT FP32 loaded' in (guard / 'logs/service.log').read_text(encoding='utf-8')
    code = 'email = "sophie.martin@example.com"'
    assert 'EMAIL:' in read(code, profile / 'example.py')
    args = {'file_path': str(target), 'content': protected}
    call({'hook_event_name': 'PreToolUse', 'tool_name': 'Write', 'tool_input': args})
    target.write_text(protected, encoding='utf-8')
    post = call({'hook_event_name': 'PostToolUse', 'tool_name': 'Write', 'tool_input': args,
                 'tool_response': {'filePath': str(target), 'type': 'create'}})
    assert 'restored' in post['additionalContext']
    assert target.read_text(encoding='utf-8') == source
    assert read(target.read_text(encoding='utf-8'), target) == protected
    vault = guard / 'vault/setup-cycle/personal.sqlite3'
    assert b'Sophie Martin' not in vault.read_bytes()
    return vault
