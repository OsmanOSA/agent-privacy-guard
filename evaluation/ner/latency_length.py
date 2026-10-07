"""Measure selected-model warm latency on contiguous published OCR excerpts."""

import json
import platform
import statistics
from datetime import datetime, timezone
from time import perf_counter

from tokenizers import Tokenizer

from .adapters import load_model
from .additional_cohort import RAW
from .decode import decode
from .fetch import BASE, sha256


def main():
    source = RAW / "europeana.bio"
    manifest = json.loads((BASE / "additional-datasets.json").read_text(encoding="utf-8"))
    dataset = next(row for row in manifest["datasets"] if row["id"] == "europeana-newspapers-fr")
    assert sha256(source.read_bytes()) == dataset["assets"][0]["sha256"]
    rows = [line.rsplit(None, 1) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    text = " ".join(token for token, tag in rows[:12000])
    directory = BASE / "models" / "distilcamembert-base-ner"
    counter = Tokenizer.from_file(str(directory / "tokenizer.json"))
    counter.no_padding()
    counter.no_truncation()
    offsets = counter.encode(text, add_special_tokens=False).offsets
    model = load_model("distilcamembert-base-ner", threads=4)
    cases = []
    for target in [500, 1000, 2000, 4000]:
        end = text.rfind(" ", 0, offsets[target - 1][1])
        content = text[:end]
        tokens = len(counter.encode(content, add_special_tokens=False).ids)
        assert target - 8 <= tokens <= target + 2
        encoded = model.tokenizer.encode(content)
        cases.append({"content": content, "target_tokens": target, "tokens": tokens,
                      "characters": len(content), "windows": 1 + len(encoded.overflowing),
                      "window_lengths": [len(window.ids) for window in [encoded, *encoded.overflowing]],
                      "text_sha256": sha256(content.encode()), "elapsed_ms": []})
    for case in cases:
        spans = decode(case["content"], model.raw(case["content"]), 0.5)
        case["prediction_sha256"] = sha256(json.dumps(spans, sort_keys=True).encode())
    for iteration in range(5):
        order = cases if iteration % 2 == 0 else list(reversed(cases))
        for case in order:
            started = perf_counter()
            spans = decode(case["content"], model.raw(case["content"]), 0.5)
            case["elapsed_ms"].append((perf_counter() - started) * 1000)
            assert sha256(json.dumps(spans, sort_keys=True).encode()) == case["prediction_sha256"]
    for case in cases:
        del case["content"]
        case.update(median_ms=statistics.median(case["elapsed_ms"]),
                    min_ms=min(case["elapsed_ms"]), max_ms=max(case["elapsed_ms"]))
    machine = json.loads((BASE / "summary-mit-20261006.json").read_text(encoding="utf-8"))["run"]["machine"]
    result = {"measured_at": datetime.now(timezone.utc).isoformat(), "model": "distilcamembert-base-ner",
              "model_sha256": sha256((directory / "model_fp32.onnx").read_bytes()),
              "tokenizer_sha256": sha256((directory / "tokenizer.json").read_bytes()),
              "harness_sha256": {name: sha256((BASE / name).read_bytes()) for name in
                                  ["latency_length.py", "token_model.py", "decode.py", "unicode_offsets.py"]},
              "source_sha256": dataset["assets"][0]["sha256"], "source_url": dataset["assets"][0]["url"],
              "source": "Contiguous prefixes of first 12000 Europeana source tokens; single-space reconstruction",
              "machine_from_prior_run_same_host": machine, "platform": platform.platform(),
              "runtime": model.backend, "threads": 4, "batch_size": 1, "passes": 5,
              "token_unit": "Detector tokenizer subwords, excluding special tokens; not agent tokens",
              "measured": "Warm tokenization + serial overlapping windows + inference + span decoding",
              "excluded": "Loading, file I/O, IPC, vault and pseudonymization; no prediction cache",
              "scope": "Latency-only single-source length probe; not F1 or a page-level benchmark",
              "cases": cases}
    output = BASE / "latency-length-20261006.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(cases, indent=2), flush=True)


if __name__ == "__main__":
    main()
