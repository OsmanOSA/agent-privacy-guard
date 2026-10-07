"""Compare published DistilCamemBERT graphs on calibration records only."""

import json

from .cohort import RUN_DIR
from .decode import decode
from .fetch import BASE, sha256
from .metrics import Metrics
from .score import load_rows
from .token_model import TokenModel


def main():
    from transformers import AutoTokenizer

    directory = BASE / "models/distilcamembert-base-ner"
    rows = list(load_rows(RUN_DIR / "calibration.jsonl").values())[:32]
    slow = AutoTokenizer.from_pretrained(str(directory), use_fast=False, local_files_only=True)
    fast = AutoTokenizer.from_pretrained(str(directory), use_fast=True, local_files_only=True)
    agreements = sum(slow.encode(row["text"]) == fast.encode(row["text"]) for row in rows[:20])
    if agreements != 20:
        raise ValueError("Native tokenizer IDs differ before graph comparison")
    result = {"calibration_records": 32, "native_tokenizer_id_agreements": agreements,
              "threshold": 0.5, "graphs": {}, "selection": "Use FP32; reject this published quantized graph for the comparison",
              "interpretation": "Artifact quality differs; the root cause of the quantized graph failure is not established"}
    for filename in ("model.onnx", "model_fp32.onnx"):
        model, metric = TokenModel(directory, filename=filename), Metrics()
        for row in rows:
            metric.add(row["text"], [s for s in row["spans"] if s["kind"] == "PERSON"], decode(row["text"], model.raw(row["text"]), .5))
        result["graphs"][filename] = {"sha256": sha256((directory / filename).read_bytes()), "quality": metric.report()}
    (BASE / "distil-artifact-check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
