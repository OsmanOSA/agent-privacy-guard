"""French PERSON detection with the evaluated DistilCamemBERT ONNX FP32 bundle.

Interface: DistilNameDetector(model_dir).find_names(text) -> list[Finding].
No downloads or PyTorch at runtime. All bundle files are verified before load;
the calibrated threshold and overlapping token windows match the evaluation.
"""

from pathlib import Path

from privacy_guard.core.findings import Finding
from privacy_guard.core.name_detector import PERSON_NAME
from privacy_guard.service.distil_files import DEFAULT_DISTIL_DIR, MANIFEST
from privacy_guard.service.model_files import ModelFiles, ModelFilesError
from privacy_guard.service.ner_spans import decode


class DistilNameDetector:
    def __init__(self, model_dir: Path = DEFAULT_DISTIL_DIR) -> None:
        if not ModelFiles(model_dir, MANIFEST).is_ready():
            raise ModelFilesError("DistilCamemBERT bundle missing or SHA-256 mismatch")
        from privacy_guard.service.ner_tokens import TokenModel

        self._model = TokenModel(model_dir, threads=4)

    def find_names(self, text: str) -> list[Finding]:
        spans = decode(text, self._model.raw(text), threshold=0.5)
        return [Finding(PERSON_NAME, span["start"], span["end"]) for span in spans]
