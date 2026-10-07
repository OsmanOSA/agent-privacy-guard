"""Load each selected implementation through the same raw-prediction interface."""

from .fetch import BASE
from .license_policy import eligible_models
from .token_model import TokenModel


class CurrentGliner2:
    def __init__(self, directory, threads=4):
        from privacy_guard.service import onnx_name_detector as implementation

        implementation.MAX_THREADS = threads
        self.implementation = implementation
        self.detector = implementation.OnnxNameDetector(directory)
        self.detector._threshold = 0.15
        self.backend = "ONNX Runtime CPU; current person-only INT4 export"

    def raw(self, text):
        words = self.implementation._split_words(text)
        candidates = [candidate for window in self.implementation._windows(words)
                      for candidate in self.detector._score(window, text)]
        kept = self.implementation._best_without_overlap(candidates)
        return {"encoding": "spans", "items": [{"start": c.start, "end": c.end,
                                                  "score": c.confidence} for c in kept]}


class LegacyGliner:
    def __init__(self, directory, threads=4):
        import torch
        from gliner import GLiNER

        torch.set_num_threads(threads)
        torch.set_num_interop_threads(1)
        self.model = GLiNER.from_pretrained(str(directory), load_tokenizer=True,
                                            local_files_only=True, map_location="cpu", strict=True)
        self.model.eval()
        self.backend = "PyTorch CPU FP32; original upstream weights"

    def raw(self, text):
        # Source sentences are short; explicitly window by source characters for
        # long inputs rather than accepting the library's implicit truncation.
        windows = [(start, text[start:start + 700]) for start in range(0, max(len(text) - 150, 1), 550)]
        items = []
        for offset, content in windows:
            for entity in self.model.predict_entities(content, ["person"], threshold=0.15):
                items.append({"start": entity["start"] + offset, "end": entity["end"] + offset,
                              "score": float(entity["score"])})
        return {"encoding": "spans", "items": items}


def load_model(name, threads=4):
    if name not in {model["id"] for model in eligible_models()}:
        raise ValueError("Model is outside the selected license policy")
    directory = BASE / "models" / name
    if name == "gliner2-privacy-filter-PII-multi":
        return CurrentGliner2(directory, threads)
    if name == "gliner_multi_pii-v1":
        return LegacyGliner(directory, threads)
    filename = "model_fp32.onnx" if name == "distilcamembert-base-ner" else "model.onnx"
    model = TokenModel(directory, threads, filename)
    variant = {"distilcamembert-base-ner": "FP32", "masker-mini": "INT4",
               "nym-pii-multilingual-small": "int8-folder export"}[name]
    model.backend += f"; {variant}"
    return model
