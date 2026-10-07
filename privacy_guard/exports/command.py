"""Run a user-requested local CSV export without printing personal content.

Interface: export_csv(source, session, filename, guard_home) -> exit code.
Run while the source session's mappings still exist. No installation is performed.
"""

from __future__ import annotations

from pathlib import Path

from privacy_guard.exports.policy import CsvExportPolicy
from privacy_guard.core.cipher import default_cipher
from privacy_guard.core.name_detector import HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from privacy_guard.exports.csv_writer import CsvWriter


def export_csv(source: Path, session: str, filename: str, guard_home: Path) -> int:
    try:
        policy = CsvExportPolicy.from_file(guard_home / "export-policy.json")
        if policy.root is None:
            raise ValueError("CSV export is disabled")
        vault = VaultStore(guard_home / "vault", default_cipher()).session(session)
        core = PrivacyCore(vault, HeuristicNameDetector())
        content = source.read_text(encoding="utf-8-sig")
        CsvWriter(policy).write(filename, content, core.restore)
    except (OSError, ValueError, RuntimeError):
        print("CSV export failed. Check the policy, session, source and unused output filename.")
        return 1
    print("CSV export completed.")
    return 0
