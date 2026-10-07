"""Score native token logits, distinguishing declared normalization from truncation."""

import numpy as np

from .token_model import TokenModel
from .unicode_offsets import complete_compositions


class NativeTokenModel(TokenModel):
    def native_deletions(self, text, missing):
        normalizer = self.tokenizer.normalizer
        return {index for index in missing if normalizer is not None
                and normalizer.normalize_str(text[index]) == ""}

    def raw(self, text):
        encoded = self.tokenizer.encode(text)
        windows, covered = [], set()
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
        required = {index for index, char in enumerate(text) if not char.isspace()}
        deleted = self.native_deletions(text, required - covered)
        missing = required - covered - deleted
        if missing:
            complete_compositions(text, windows, self.tokenizer.normalizer, missing)
            covered = {index for window in windows for row in window for index in range(row["start"], row["end"])}
            if required - covered - deleted:
                raise ValueError("Tokenizer windows did not cover the complete input")
        # Deleted glyphs retain their original source positions and gold labels.
        # No span is expanded to award model credit for a removed glyph.
        return {"encoding": "tokens", "windows": windows,
                "native_normalizer_deleted_positions": sorted(deleted)}
