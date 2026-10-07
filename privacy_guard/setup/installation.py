"""Activate a verified Windows bundle through the existing Claude Code installer."""

import json
import os
import shutil
from pathlib import Path

from privacy_guard.claude_code.installer import ClaudeCodeInstaller, PACKAGE_DIR
from privacy_guard.claude_code.settings_file import SettingsFile
from privacy_guard.claude_code.vault_format import VaultCompatibility
from privacy_guard.claude_code import registration
from privacy_guard.core.cipher import default_cipher
from privacy_guard.notifications.config import configure
from privacy_guard.notifications.lifecycle import stop_worker
from privacy_guard.service.channel import ServiceChannel
from privacy_guard.service.client import ServiceClient
from privacy_guard.service.distil_files import DISTIL_DIRECTORY, MANIFEST
from privacy_guard.service.model_files import ModelFiles
from privacy_guard.service.ner_policy import record_model
from privacy_guard.setup.bundle import check_runtime, verify_bundle
from privacy_guard.setup.transaction import installation_transaction


def claude_directory(user_home: Path) -> Path:
    configured = os.environ.get('CLAUDE_CONFIG_DIR')
    return Path(configured).expanduser().resolve() if configured else user_home / '.claude'


def preflight(bundle: Path, user_home: Path):
    manifest = verify_bundle(bundle)
    directory = claude_directory(user_home)
    available = (directory.is_dir() or shutil.which('claude') or
                 (user_home / '.local/bin/claude.exe').is_file() or
                 any((user_home / '.vscode/extensions').glob('anthropic.claude-code-*')))
    if not available:
        raise RuntimeError('Install and open Claude Code once, then run Privacy Guard setup again')
    settings = SettingsFile(directory / 'settings.json').load()
    if not isinstance(settings, dict) or settings.get('disableAllHooks'):
        raise RuntimeError('Claude Code settings disable hooks or have an invalid structure')
    default_cipher()
    VaultCompatibility(user_home / '.privacy-guard', PACKAGE_DIR).check()
    return manifest, directory


def install(bundle: Path, user_home: Path):
    manifest, directory = preflight(bundle, user_home)
    home = user_home / '.privacy-guard'
    python = bundle / 'runtime/python.exe'
    installer = ClaudeCodeInstaller(directory, home, python)
    # Stop processes before copying rollback snapshots or changing engine files.
    ServiceClient(ServiceChannel(home / 'run')).stop()
    stop_worker(home / 'notifications')
    # Loading a second model beside the active one can exhaust Windows commit
    # memory. Stop the old detector before probing this bundle.
    check_runtime(bundle)
    directory.mkdir(parents=True, exist_ok=True)
    with installation_transaction(home, directory / 'settings.json'):
        ModelFiles(home / 'models' / DISTIL_DIRECTORY, MANIFEST).fetch(str(bundle / 'model'))
        record_model(home)
        if (bundle / 'data').is_dir():
            (home / 'data').mkdir(exist_ok=True)
            for name in ('insee-names.sqlite', 'insee-names.source.json', 'INSEE-data-NOTICE.txt'):
                shutil.copyfile(bundle / 'data' / name, home / 'data' / name)
        installer.install()
        preferences = home / 'notifications/settings.json'
        if not preferences.exists():
            configure(home / 'notifications', 'background', 'card')
        if not all(installer.status().values()):
            raise RuntimeError('Hook registration did not complete')
        receipt = {'schema': 1, 'version': manifest['version'], 'bundle': str(bundle),
                   'claude_directory': str(directory), 'python': str(python)}
        (home / 'windows-setup.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def uninstall(bundle: Path, user_home: Path):
    home = user_home / '.privacy-guard'
    receipt_path = home / 'windows-setup.json'
    if not receipt_path.exists():
        return
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if Path(receipt['bundle']).resolve() != bundle.resolve():
        raise RuntimeError('A different installed version owns the active integration')
    settings = SettingsFile(Path(receipt['claude_directory']) / 'settings.json')
    current = settings.load()
    expected = f'"{(bundle / "runtime/python.exe").as_posix()}" "{(home / "app").as_posix()}"'
    commands = [hook.get('command', '') for event in registration.HOOK_EVENTS
                for group in current.get('hooks', {}).get(event, [])
                for hook in group.get('hooks', [])]
    if any(registration.MARKER in command and command != expected for command in commands):
        raise RuntimeError('Another Privacy Guard installation now owns the hooks')
    # Only remove this product's hooks. Other settings and retained mappings survive.
    ServiceClient(ServiceChannel(home / 'run')).stop()
    stop_worker(home / 'notifications')
    updated = registration.unregister(current)
    if current != updated:
        settings.save(updated)
    receipt_path.unlink()


def status(user_home: Path):
    home = user_home / '.privacy-guard'
    receipt = json.loads((home / 'windows-setup.json').read_text(encoding='utf-8'))
    settings = SettingsFile(Path(receipt['claude_directory']) / 'settings.json').load()
    if not all(registration.registered_events(settings).values()) or settings.get('disableAllHooks'):
        raise RuntimeError('Hook registration is incomplete or disabled')
    if not ModelFiles(home / 'models' / DISTIL_DIRECTORY, MANIFEST).is_ready():
        raise RuntimeError('The installed name model is missing or corrupted')
    client = ServiceClient(ServiceChannel(home / 'run'), python=Path(receipt['python']))
    if not client.find_names('Madame Sophie Martin habite Paris.'):
        raise RuntimeError('The installed name detector did not answer the status check')
    return receipt['version']
