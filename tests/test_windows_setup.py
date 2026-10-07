import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from privacy_guard.setup.transaction import installation_transaction
from privacy_guard.setup.bundle import verify_bundle
from privacy_guard.setup.installation import preflight, uninstall
from privacy_guard.service.runtime_python import bundled_python


class WindowsSetupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / '.privacy-guard'
        self.settings = self.root / '.claude/settings.json'
        self.settings.parent.mkdir()
        self.settings.write_bytes(b'{"theme":"dark"}')

    def test_failed_upgrade_restores_app_settings_and_preserves_vault(self):
        app = self.home / 'app'
        app.mkdir(parents=True)
        (app / 'engine.py').write_text('old engine')
        vault = self.home / 'vault/session/value'
        vault.parent.mkdir(parents=True)
        vault.write_bytes(b'encrypted fixture')
        with self.assertRaisesRegex(RuntimeError, 'installation failed'):
            with installation_transaction(self.home, self.settings):
                (app / 'engine.py').write_text('new engine')
                (app / 'new.py').write_text('partial upgrade')
                self.settings.write_text('{}')
                (self.home / 'ner-model.json').write_text('{}')
                raise RuntimeError('installation failed')
        self.assertEqual((app / 'engine.py').read_text(), 'old engine')
        self.assertFalse((app / 'new.py').exists())
        self.assertEqual(self.settings.read_bytes(), b'{"theme":"dark"}')
        self.assertEqual(vault.read_bytes(), b'encrypted fixture')
        self.assertFalse((self.home / 'ner-model.json').exists())
        self.assertFalse((self.home / 'setup.lock').exists())

    def test_concurrent_setup_is_refused_without_removing_owner_lock(self):
        with installation_transaction(self.home, self.settings):
            with self.assertRaises(FileExistsError):
                with installation_transaction(self.home, self.settings):
                    self.fail('Concurrent setup acquired the lock')
            self.assertTrue((self.home / 'setup.lock').exists())

    def test_payload_path_escape_is_rejected(self):
        bundle = self.root / 'bundle'
        bundle.mkdir()
        (bundle / 'payload.json').write_text(json.dumps({'schema': 1,
            'product': 'agent-privacy-guard', 'files': {'../outside': '0' * 64}}))
        with self.assertRaisesRegex(ValueError, 'Invalid payload path'):
            verify_bundle(bundle)

    def test_corrupted_file_is_rejected_before_installation(self):
        bundle = self.root / 'bundle'
        bundle.mkdir()
        (bundle / 'engine.py').write_text('corrupted')
        (bundle / 'payload.json').write_text(json.dumps({'schema': 1,
            'product': 'agent-privacy-guard', 'files': {'engine.py': '0' * 64}}))
        with self.assertRaisesRegex(ValueError, 'failed verification'):
            verify_bundle(bundle)
        self.assertEqual(self.settings.read_bytes(), b'{"theme":"dark"}')

    def test_disabled_hooks_do_not_get_overridden(self):
        self.settings.write_text('{"disableAllHooks":true}')
        with patch('privacy_guard.setup.installation.verify_bundle', return_value={}):
            with patch.dict('os.environ', {}, clear=True):
                with self.assertRaisesRegex(RuntimeError, 'disable hooks'):
                    preflight(self.root / 'bundle', self.root)
        self.assertFalse(self.home.exists())

    def test_old_uninstaller_cannot_remove_new_installation(self):
        self.home.mkdir()
        (self.home / 'windows-setup.json').write_text(json.dumps({'bundle':str(self.root/'new')}))
        with self.assertRaisesRegex(RuntimeError, 'different installed version'):
            uninstall(self.root / 'old', self.root)
        self.assertTrue((self.home / 'windows-setup.json').exists())

    def test_uninstall_keeps_other_hooks_and_personal_data(self):
        bundle = self.root / 'bundle'
        self.home.mkdir()
        (self.home / 'windows-setup.json').write_text(json.dumps(
            {'bundle':str(bundle),'claude_directory':str(self.settings.parent)}))
        command = f'"{(bundle / "runtime/python.exe").as_posix()}" "{(self.home / "app").as_posix()}"'
        own = {'hooks':[{'command':command}]}
        other = {'hooks':[{'command':'my-other-tool'}]}
        self.settings.write_text(json.dumps({'model':'opus','hooks':{'PostToolUse':[own,other]}}))
        vault = self.home / 'vault/keep'
        vault.parent.mkdir()
        vault.write_bytes(b'opaque bytes')
        with patch('privacy_guard.setup.installation.ServiceClient'), patch('privacy_guard.setup.installation.stop_worker'):
            uninstall(bundle, self.root)
        self.assertEqual(json.loads(self.settings.read_text()),{'model':'opus','hooks':{'PostToolUse':[other]}})
        self.assertEqual(vault.read_bytes(),b'opaque bytes')

    def test_uninstaller_refuses_hooks_taken_over_by_a_manual_install(self):
        bundle = self.root / 'bundle'
        self.home.mkdir()
        (self.home / 'windows-setup.json').write_text(json.dumps(
            {'bundle': str(bundle), 'claude_directory': str(self.settings.parent)}))
        self.settings.write_text(json.dumps({'hooks': {'PreToolUse': [
            {'hooks': [{'command': 'other-python .privacy-guard/app'}]}]}}))
        before = self.settings.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'now owns the hooks'):
            uninstall(bundle, self.root)
        self.assertEqual(self.settings.read_bytes(), before)
        self.assertTrue((self.home / 'windows-setup.json').exists())

    def test_bundled_interpreter_is_selected_only_with_valid_marker(self):
        python = self.root / 'python.exe'
        self.assertIsNone(bundled_python(str(python)))
        marker = self.root / 'privacy-guard-runtime.json'
        marker.write_text('{"product":"another-app"}')
        self.assertIsNone(bundled_python(str(python)))
        marker.write_text(json.dumps({'schema':1,'product':'agent-privacy-guard','model_runtime':True}))
        self.assertEqual(bundled_python(str(python)), python)
