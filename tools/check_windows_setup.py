"""Install a TEST-IDENTITY setup in an isolated profile, exercise it, then uninstall."""

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from windows_setup_cycle import exercise


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('setup', type=Path)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    if not args.setup.name.startswith('PrivacyGuard-Test-'):
        parser.error('Only a --test-build artifact is allowed')
    root = args.work.resolve()
    root.mkdir(parents=True, exist_ok=False)
    profile, app = root / 'profile', root / 'application'
    settings = profile / '.claude/settings.json'
    settings.parent.mkdir(parents=True)
    original = {'model': 'opus', 'hooks': {'PreToolUse': [
        {'hooks': [{'type': 'command', 'command': 'echo unrelated-hook'}]}]}}
    settings.write_text(json.dumps(original))
    env = dict(os.environ, USERPROFILE=str(profile), HOME=str(profile),
               CLAUDE_CONFIG_DIR=str(settings.parent))
    global_files = [Path.home() / p for p in (
        '.claude/settings.json', '.privacy-guard/windows-setup.json', '.privacy-guard/ner-model.json')]
    before = list(map(fingerprint, global_files))
    setup = args.setup.resolve()

    def run(command):
        command = list(map(str, command))
        # NSIS /D and _? consume the remainder verbatim, without enclosing quotes.
        if command[-1].startswith(('/D=', '_?=')):
            command = subprocess.list2cmdline(command[:-1]) + ' ' + command[-1]
        result = subprocess.run(command, env=env, capture_output=True, timeout=240)
        if result.returncode:
            log = Path(tempfile.gettempdir()) / 'PrivacyGuardSetupTest-setup-error.txt'
            detail = (log.read_text(encoding='utf-16-le') if log.exists()
                      else result.stderr.decode('utf-8', errors='replace'))
            raise RuntimeError(f'Setup check failed ({result.returncode}): {detail}')

    run([setup, '/S', f'/D={app}'])
    receipt_path = profile / '.privacy-guard/windows-setup.json'
    receipt = json.loads(receipt_path.read_text())
    bundle = Path(receipt['bundle'])
    python = bundle / 'runtime/python.exe'
    run([python, '-m', 'privacy_guard.setup', 'status'])
    assert (profile / '.privacy-guard/data/insee-names.sqlite').exists()
    assert json.loads(settings.read_text())['model'] == 'opus'
    vault = exercise(python, profile, env)
    stored = fingerprint(vault)
    run([setup, '/S', f'/D={app}'])
    assert fingerprint(vault) == stored, 'Reinstallation changed the vault'
    assert json.loads((profile / '.privacy-guard/notifications/settings.json').read_text())['mode'] == 'off'
    run([python, '-m', 'privacy_guard.setup', 'status'])
    run([app / 'Uninstall.exe', '/S', f'_?={app}'])
    deadline = time.monotonic() + 15
    while receipt_path.exists() and time.monotonic() < deadline:
        time.sleep(.1)
    assert not receipt_path.exists()
    assert not bundle.exists(), 'Runtime files remain after removal'
    assert json.loads(settings.read_text()) == original
    assert fingerprint(vault) == stored, 'Uninstall changed retained personal mappings'
    assert list(map(fingerprint, global_files)) == before, 'The real profile changed'
    print(json.dumps({'result': 'passed', 'checks': [
        'silent setup', 'bundled model and INSEE', 'document and Python hooks',
        'restoration and reread', 'reinstallation and vault preservation',
        'uninstall and unrelated settings preservation', 'real profile unchanged']}))


if __name__ == '__main__':
    main()
