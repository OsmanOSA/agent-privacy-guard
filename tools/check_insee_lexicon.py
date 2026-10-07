"""Compare optional INSEE complement on the same corpus; record lookup latency."""

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path, PurePath

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
from benchmark.annotation import load_corpus
from benchmark.scoring import Report
from privacy_guard.claude_code.document_scope import DOCUMENT_EXTENSIONS
from privacy_guard.core.detector import SensitiveDataDetector
from privacy_guard.core.insee_names import InseeNameDetector, local_name_detector
from privacy_guard.core.name_detector import CombinedNameDetector, HeuristicNameDetector
from privacy_guard.core.name_lexicon import LEXICON_FILE


def digest(data):
    return hashlib.sha256(data).hexdigest()


def compare(home):
    documents = list(load_corpus(PROJECT / 'benchmark/corpus'))
    baseline, supplemented = HeuristicNameDetector(), local_name_detector(home)
    from privacy_guard.service.distil_name_detector import DistilNameDetector
    model = DistilNameDetector()
    profiles = {
        'rules_without_insee': (baseline, baseline),
        'rules_with_insee': (supplemented, supplemented),
        'model_without_insee': (baseline, CombinedNameDetector([baseline, model])),
        'model_with_insee': (supplemented, CombinedNameDetector([supplemented, model])),
    }
    scores = {}
    for label, (quick, detailed) in profiles.items():
        quick, detailed = SensitiveDataDetector(quick), SensitiveDataDetector(detailed)
        report = Report()
        for document in documents:
            detector = detailed if PurePath(document.name).suffix.lower() in DOCUMENT_EXTENSIONS else quick
            report.add(document, detector.find(document.text))
        scores[label] = {kind: dict(expected=score.expected, hidden=score.hidden,
                                   found=score.found, justified=score.justified,
                                   recall=score.recall, precision=score.precision)
                         for kind, score in sorted(report.scores.items())}
    return scores


def latency(path):
    from evaluation.ner.additional_cohort import RAW
    reference = json.loads((PROJECT / 'evaluation/ner/latency-length-20261006.json').read_text())
    raw = (RAW / 'europeana.bio').read_bytes()
    assert digest(raw) == reference['source_sha256']
    joined = ' '.join(line.rsplit(None, 1)[0] for line in raw.decode('utf-8').splitlines() if line.strip())
    case = reference['cases'][-1]
    excerpt = joined[:case['characters']]
    assert digest(excerpt.encode()) == case['text_sha256']
    detector = InseeNameDetector(path)
    rows = []
    for name, text in [
        ('synthetic_person_fields', '{"first_name":"alice", "last_name":"dupont"}'),
        ('synthetic_code_1000_lines', 'tokens_estimated=tokens_estimated\n' * 1000),
        ('public_europeana_3997_model_tokens', excerpt),
    ]:
        start = time.perf_counter()
        findings = detector.find_names(text)
        first_ms = (time.perf_counter() - start) * 1000
        observations = []
        for _ in range(50):
            start = time.perf_counter()
            assert detector.find_names(text) == findings
            observations.append((time.perf_counter() - start) * 1000)
        rows.append(dict(case=name, characters=len(text), text_sha256=digest(text.encode()),
                         findings=len(findings), first_observation_ms=first_ms,
                         median_ms=statistics.median(observations),
                         p95_ms=sorted(observations)[47], observations_ms=observations))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lexicon-home', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    path = args.lexicon_home / 'data' / LEXICON_FILE
    result = dict(measured_utc=datetime.now(timezone.utc).isoformat(), source_only=True, global_deployment=False,
                  platform=platform.platform(), python=platform.python_version(),
                  lexicon=json.loads(path.with_suffix('.source.json').read_text(encoding='utf-8')),
                  corpus='benchmark/corpus; same inputs and modes with optional index disabled/enabled',
                  quality_metric='Existing annotated overlap coverage, not exact-span F1; synthetic regression corpus',
                  quality=compare(args.lexicon_home), latency=latency(path),
                  latency_scope='INSEE complement only; no NER, vault, IPC, hook startup or network; uncontrolled Windows load',
                  runtime_hashes={file: digest((PROJECT / file).read_bytes()) for file in [
                      'privacy_guard/core/name_lexicon.py', 'privacy_guard/core/insee_names.py',
                      'privacy_guard/core/detector.py', 'privacy_guard/claude_code/hook.py',
                      'privacy_guard/service/__main__.py', 'tools/prepare_insee_lexicon.py',
                      'tools/check_insee_lexicon.py', 'tests/test_insee_names.py']},
                  limitations=['Context-dependent matching; ambiguous dictionary words intentionally not blanket-masked',
                               'No cross-call name learning or image extraction',
                               'INSEE files are incomplete public name statistics, not labelled NER reference corpora',
                               'Code is MIT; INSEE source attribution/reuse terms remain separate'])
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(quality={label: score['name'] for label, score in result['quality'].items()},
                          latency=[{k: v for k, v in row.items() if k != 'observations_ms'} for row in result['latency']]), indent=2))


if __name__ == '__main__':
    main()
