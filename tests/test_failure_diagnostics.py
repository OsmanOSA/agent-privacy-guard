"""Fixed failure stages/categories, never exception messages or inspected data."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from privacy_guard.claude_code.hook import run
from privacy_guard.core.vault import VaultStore
from privacy_guard.journal import EventJournal
from tests.fakes import RecordingNameService, ReversingCipher

PRIVATE = 'alice.private@example.org'


class FailureDiagnosticsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.journal = EventJournal(self.root / 'logs/guard.log')
        self.vaults = VaultStore(self.root / 'vault', ReversingCipher())
        self.names = RecordingNameService()

    def call(self, payload, journal=None, vaults=None, names=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        code = run(io.StringIO(payload if isinstance(payload, str) else json.dumps(payload)),
                   stdout, stderr, journal or self.journal, vaults or self.vaults, names or self.names)
        self.assertNotIn(PRIVATE, stdout.getvalue() + stderr.getvalue())
        return code, json.loads(stdout.getvalue()) if stdout.getvalue() else {}

    def row(self):
        content = (self.root / 'logs/failures.jsonl').read_text(encoding='utf-8')
        self.assertNotIn(PRIVATE, content)
        self.assertNotIn(str(self.root), content)
        row = json.loads(content.splitlines()[-1])
        self.assertEqual(set(row), {'timestamp', 'event', 'tool', 'stage', 'category'})
        return row

    def test_detection_failure_is_identified_and_still_blocks(self):
        names = Mock()
        names.find_names.side_effect = RuntimeError(PRIVATE)
        _, reply = self.call(dict(hook_event_name='PostToolUse', session_id='a', tool_name='Read',
                                  tool_input={'file_path': 'document.txt'}, tool_response={'content': 'Nom : Alice'}), names=names)
        self.assertFalse(reply['continue'])
        self.assertEqual(self.row()['stage'], 'detection')

    def test_parsing_failure_is_identified(self):
        self.assertEqual(self.call('{invalid ' + PRIVATE), (2, {}))
        self.assertEqual(self.row()['stage'], 'payload_parse')

    def test_event_journal_error_is_identified(self):
        self.journal.record = Mock(side_effect=PermissionError(PRIVATE))
        self.call(dict(hook_event_name='PostToolUse', session_id='a', tool_name='Bash', tool_response=PRIVATE))
        self.assertEqual((self.row()['stage'], self.row()['category']), ('event_journal', 'permission'))

    def test_diagnostic_failure_cannot_replace_the_stop_response(self):
        journal = Mock()
        journal.record.side_effect = OSError(PRIVATE)
        journal.record_failure.side_effect = OSError(PRIVATE)
        _, reply = self.call(dict(hook_event_name='PostToolUse', session_id='a', tool_name='Bash',
                                  tool_response=PRIVATE), journal=journal)
        self.assertFalse(reply['continue'])

    def test_corrupt_known_name_storage_is_identified(self):
        from privacy_guard.core.privacy_core import PrivacyCore
        PrivacyCore(self.vaults.session('a'), self.names).protect('Nom : Alice')
        (self.root / 'vault/a/personal.sqlite3').write_bytes(b'corrupt')
        _, reply = self.call(dict(hook_event_name='PostToolUse', session_id='a', tool_name='Bash',
                                  tool_response='alice'))
        self.assertFalse(reply['continue'])
        self.assertEqual((self.row()['stage'], self.row()['category']), ('session_names', 'sqlite_corrupt'))

    def test_untrusted_event_tool_stage_and_category_are_not_logged(self):
        self.journal.record_failure(PRIVATE, PRIVATE, PRIVATE, PRIVATE)
        self.assertEqual({k: self.row()[k] for k in ('event', 'tool', 'stage', 'category')},
                         dict(event='unknown', tool='unknown', stage='unknown', category='unexpected'))

    def test_restoration_failure_is_logged_without_echoing_values(self):
        from privacy_guard.claude_code.write_restoration import process_write_result
        from privacy_guard.core.privacy_core import PrivacyCore
        writer = Mock()
        writer.restore.side_effect = PermissionError(PRIVATE)
        core = PrivacyCore(self.vaults.session('a'), self.names)
        reply = process_write_result(dict(hook_event_name='PostToolUse', tool_name='Write', tool_response={}),
                                     core, writer, failures=self.journal)
        self.assertNotIn(PRIVATE, reply.stdout)
        self.assertEqual((self.row()['stage'], self.row()['category']), ('restoration', 'permission'))

    def test_sensitive_failed_tool_stop_has_diagnostic_category(self):
        self.call(dict(hook_event_name='PostToolUseFailure', session_id='a', tool_name='Bash', error=PRIVATE))
        self.assertEqual((self.row()['stage'], self.row()['category']), ('failed_tool', 'sensitive_result'))

    def test_service_failure_preserves_remote_stage_and_omits_exception_text(self):
        from privacy_guard.service.server import _BackgroundLoad, _find_names
        from privacy_guard.service.client import ServiceClient, ServiceError
        from privacy_guard.service.channel import ServiceChannel
        from privacy_guard.diagnostics import failure_details
        load = Mock(side_effect=RuntimeError(PRIVATE))
        answer = _find_names(_BackgroundLoad(load), 'Nom : Alice')
        self.assertEqual(answer, dict(error='runtime_error', stage='model_loading'))
        self.assertNotIn(PRIVATE, json.dumps(answer))
        client = ServiceClient(ServiceChannel(self.root / 'run'))
        client._request = Mock(return_value=answer)
        with self.assertRaises(ServiceError) as caught:
            client.find_names('Nom : Alice')
        self.assertEqual(failure_details(caught.exception), ('model_loading', 'runtime_error'))

    def test_input_read_failure_is_logged_and_blocks(self):
        source = Mock()
        source.read.side_effect = OSError(PRIVATE)
        self.assertEqual(run(source, io.StringIO(), io.StringIO(), self.journal, self.vaults, self.names), 2)
        rows = [json.loads(line) for line in (self.root / 'logs/failures.jsonl').read_text().splitlines()]
        self.assertIn('input_read', [row['stage'] for row in rows])


if __name__ == '__main__':
    unittest.main()
