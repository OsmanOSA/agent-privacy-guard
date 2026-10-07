"""Isolate encrypted name reuse cost on one frozen public excerpt, with real DPAPI."""

import argparse
import hashlib
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
from evaluation.ner.additional_cohort import RAW
from privacy_guard.core.bound_values import BoundValues
from privacy_guard.core.cipher import default_cipher
from privacy_guard.core.name_detector import CombinedNameDetector, HeuristicNameDetector
from privacy_guard.core.privacy_core import PrivacyCore
from privacy_guard.core.vault import VaultStore
from privacy_guard.service.cached_names import CachedNameDetector
from privacy_guard.service.distil_name_detector import DistilNameDetector


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reference = json.loads((PROJECT / 'evaluation/ner/latency-length-20261006.json').read_text())
    raw = (RAW / 'europeana.bio').read_bytes()
    assert digest(raw) == reference['source_sha256']
    text = ' '.join(line.rsplit(None, 1)[0] for line in raw.decode('utf-8').splitlines() if line.strip())
    case = reference['cases'][-1]
    text = text[:case['characters']]
    assert digest(text.encode()) == case['text_sha256']
    names = CachedNameDetector(CombinedNameDetector([HeuristicNameDetector(), DistilNameDetector()]))
    names.find_names(text)
    with tempfile.TemporaryDirectory() as directory:
        root, cipher = Path(directory), default_cipher()
        def core():
            return PrivacyCore(VaultStore(root, cipher).session('public-probe'), names)
        protected = core().protect(text)
        assert core().restore(protected) == text
        count = len(BoundValues(VaultStore(root, cipher).session('public-probe')).known_names())
        observations = {'reuse_disabled_for_comparison': [], 'reuse_enabled': []}
        # Alternate runs to reduce order bias; new core/vault per run models hook reopening.
        for _ in range(10):
            for enabled in (False, True):
                engine = core()
                context = patch.object(BoundValues, 'known_names', return_value=set()) if not enabled else patch.object(
                    BoundValues, 'known_names', BoundValues.known_names)
                with context:
                    start = time.perf_counter()
                    current = engine.protect(text)
                    elapsed = (time.perf_counter() - start) * 1000
                assert current == protected
                assert engine.restore(current) == text
                observations['reuse_enabled' if enabled else 'reuse_disabled_for_comparison'].append(elapsed)
    result = dict(text_sha256=case['text_sha256'], tokens=case['tokens'], committed_unique_names=count,
                  scope='Warm in-process reread; actual DPAPI, reopened vault; exact restoration and stable tokens',
                  disabled_scope='Same runtime with committed-name lookup disabled for a cost comparison only',
                  excluded='NER/loading, hook startup, IPC and model networking',
                  observations_ms=observations, median_ms={key: statistics.median(values) for key, values in observations.items()},
                  limitations='One public excerpt, ten interleaved pairs, uncontrolled Windows load; not a total hook latency guarantee')
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'observations_ms'}, indent=2))


if __name__ == '__main__':
    main()
