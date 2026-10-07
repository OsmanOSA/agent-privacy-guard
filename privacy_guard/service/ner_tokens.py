"""Run published ONNX token classifiers on complete overlapping text windows."""

import json

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from .ner_unicode import complete_compositions, must_be_covered, tokenizable


class TokenModel:
    def __init__(self, directory, threads=4, filename="model.onnx"):
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.no_padding()
        self.tokenizer.enable_truncation(max_length=512, stride=64)
        config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
        self.labels = config["id2label"]
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(directory / filename), options,
                                            providers=["CPUExecutionProvider"])
        self.inputs = {item.name for item in self.session.get_inputs()}
        self.backend = "ONNX Runtime CPU"

    def raw(self, text):
        encoded = self.tokenizer.encode(tokenizable(text))
        windows = []
        covered = set()
        for window in [encoded, *encoded.overflowing]:
            arrays = {"input_ids": window.ids, "attention_mask": window.attention_mask,
                      "token_type_ids": window.type_ids}
            feed = {name: np.asarray([arrays[name]], dtype=np.int64) for name in self.inputs}
            logits = self.session.run(None, feed)[0][0]
            probabilities = np.exp(logits - logits.max(axis=-1, keepdims=True))
            probabilities /= probabilities.sum(axis=-1, keepdims=True)
            rows = []
            for (start, end), special, scores in zip(window.offsets, window.special_tokens_mask, probabilities):
                if special or start == end:
                    continue
                index = int(scores.argmax())
                rows.append({"label": self.labels[str(index)], "start": start,
                             "end": end, "score": float(scores[index])})
                covered.update(range(start, end))
            windows.append(rows)
        required = {index for index, char in enumerate(text) if must_be_covered(char)}
        if required - covered:
            complete_compositions(text, windows, self.tokenizer.normalizer, required - covered)
            covered = {index for window in windows for row in window for index in range(row["start"], row["end"])}
            if required - covered:
                raise ValueError("Tokenizer windows did not cover the complete input")
        return {"encoding": "tokens", "windows": windows}
