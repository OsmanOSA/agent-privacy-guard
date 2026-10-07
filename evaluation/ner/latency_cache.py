"""Measure exact-text caching with the selected model, outside production."""

import json
import statistics
from datetime import datetime, timezone
from time import perf_counter

from privacy_guard.core.findings import Finding
from privacy_guard.service.cached_names import CachedNameDetector

from .adapters import load_model
from .additional_cohort import RAW
from .decode import decode
from .fetch import BASE, sha256


class SelectedNames:
    def __init__(self):
        self.model = load_model("distilcamembert-base-ner", threads=4)
        self.calls = 0

    def find_names(self, text):
        self.calls += 1
        spans = decode(text, self.model.raw(text), 0.5)
        return [Finding("person_name", span["start"], span["end"]) for span in spans]


def timed(detector, text):
    started = perf_counter()
    findings = detector.find_names(text)
    return findings, (perf_counter() - started) * 1000


def main():
    reference = json.loads((BASE / "latency-length-20261006.json").read_text(encoding="utf-8"))
    case = reference["cases"][-1]
    source = RAW / "europeana.bio"
    assert sha256(source.read_bytes()) == reference["source_sha256"]
    rows = [line.rsplit(None, 1) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    text = " ".join(token for token, tag in rows[:12000])[:case["characters"]]
    assert sha256(text.encode()) == case["text_sha256"]
    model = BASE / "models" / "distilcamembert-base-ner" / "model_fp32.onnx"
    assert sha256(model.read_bytes()) == reference["model_sha256"]
    detector = SelectedNames()
    detector.find_names(text)
    expected, uncached_ms = timed(detector, text)
    cache = CachedNameDetector(detector)
    first, miss_ms = timed(cache, text)
    assert first == expected
    hit_ms = []
    for _ in range(5):
        findings, elapsed = timed(cache, text)
        assert findings == expected
        hit_ms.append(elapsed)
    assert detector.calls == 3
    findings_digest = sha256(json.dumps([(f.kind, f.start, f.end) for f in expected]).encode())
    result = {"measured_at": datetime.now(timezone.utc).isoformat(), "model": reference["model"],
              "model_sha256": reference["model_sha256"], "text_sha256": case["text_sha256"],
              "source_sha256": reference["source_sha256"], "tokens": case["tokens"],
              "characters": case["characters"], "windows": case["windows"],
              "findings": len(expected), "prediction_sha256": findings_digest,
              "adapter_sha256": sha256((BASE.parent.parent / "privacy_guard/service/cached_names.py").read_bytes()),
              "harness_sha256": sha256((BASE / "latency_cache.py").read_bytes()),
              "cpu_threads": 4, "warm_uncached_ms": uncached_ms, "cache_miss_ms": miss_ms,
              "hit_ms": hit_ms, "hit_median_ms": statistics.median(hit_ms),
              "inference_calls": detector.calls, "equality_checked": True,
              "scope": "One published OCR excerpt; cache wrapper only; excludes IPC, rules, vault, pseudonymization and model loading"}
    (BASE / "latency-cache-20261006.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
