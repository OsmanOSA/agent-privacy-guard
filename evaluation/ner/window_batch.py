"""Local experiment: bounded window batches with unchanged span decoding."""

import numpy as np

from privacy_guard.service.ner_tokens import TokenModel
from privacy_guard.service.ner_unicode import complete_compositions


class WindowBatchModel(TokenModel):
    def __init__(self, directory, batch_size):
        super().__init__(directory, threads=4)
        if batch_size not in (1, 2, 4):
            raise ValueError("Experiment supports batch sizes 1, 2 or 4")
        self.batch_size = batch_size
        self.pad_id = self.tokenizer.token_to_id("<pad>")
        if self.pad_id is None:
            raise ValueError("Tokenizer has no padding token")
        for item in self.session.get_inputs():
            if isinstance(item.shape[0], int) and item.shape[0] != batch_size:
                raise ValueError("ONNX graph has a fixed incompatible batch dimension")

    def _infer(self, group):
        width = max(len(window.ids) for window in group)
        arrays = {}
        for name in self.inputs:
            fill = self.pad_id if name == "input_ids" else 0
            arrays[name] = np.full((len(group), width), fill, dtype=np.int64)
        for row, window in enumerate(group):
            values = {"input_ids": window.ids, "attention_mask": window.attention_mask,
                      "token_type_ids": window.type_ids}
            for name in self.inputs:
                arrays[name][row, :len(window.ids)] = values[name]
        logits = self.session.run(None, arrays)[0]
        return [(window, scores[:len(window.ids)]) for window, scores in zip(group, logits)]

    def raw(self, text):
        encoded = self.tokenizer.encode(text)
        encoded_windows = [encoded, *encoded.overflowing]
        windows, covered = [], set()
        for offset in range(0, len(encoded_windows), self.batch_size):
            for window, logits in self._infer(encoded_windows[offset:offset + self.batch_size]):
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
        required = {index for index, char in enumerate(text) if not char.isspace()}
        if required - covered:
            complete_compositions(text, windows, self.tokenizer.normalizer, required - covered)
            covered = {index for window in windows for row in window for index in range(row["start"], row["end"])}
            if required - covered:
                raise ValueError("Tokenizer windows did not cover the complete input")
        return {"encoding": "tokens", "windows": windows}
