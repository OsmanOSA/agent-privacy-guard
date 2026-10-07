"""Pinned DistilCamemBERT FP32 bundle, separate from the legacy GLiNER files."""

from pathlib import Path

DISTIL_DIRECTORY = "distilcamembert-ner"
DEFAULT_DISTIL_DIR = Path.home() / ".privacy-guard" / "models" / DISTIL_DIRECTORY
UPSTREAM = "cmarkea/distilcamembert-base-ner"
REVISION = "e539d952f70088b450c300c28ba455da87f2dc4b"
MANIFEST = {
    "config.json": "103f36a11079994f128a20c46cb388912dc9d481fded4ce12fbfe2d9f63d2662",
    "model.onnx": "666ce15c968ca49874d2449aa9b83164dbb1126090d012dda7c35b2ef3672e1d",
    "tokenizer.json": "87d51d8e30bfe0b07f9042dd67ca7ee52510c0f8f91d103980e9112e83beced1",
    "README.upstream.md": "e115be795fa5af7ff5db3da46db0352d6f71724197a1b263be890d7d2a131ec3",
}
