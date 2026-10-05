"""Builds the person-name model used by the background service.

Converts GLiNER2-PII (PyTorch, ~1.2 GB, ~10 s to load) into a single 4-bit ONNX
graph (~250 MB, ~1 s to load) that the service runs without PyTorch.

Runs once, at install time, in an environment that has PyTorch and gliner2:
    python tools/build_name_model.py [--out DIR]

The graph covers everything that needs the model's weights: encoder, span
representations, count prediction and the "person" projection. Text preparation
and span decoding stay in plain Python (privacy_guard/service/onnx_name_detector.py),
driven by the config.json written here.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")

import onnx  # noqa: E402
import torch  # noqa: E402
from gliner2 import GLiNER2  # noqa: E402
from gliner2.training.trainer import ExtractorCollator  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from onnxruntime.quantization.matmul_nbits_quantizer import (  # noqa: E402
    DefaultWeightOnlyQuantConfig,
    MatMulNBitsQuantizer,
)
from transformers.modeling_utils import no_init_weights  # noqa: E402

MODEL_ID = "fastino/gliner2-privacy-filter-PII-multi"
LABEL = "person"
DEFAULT_OUT = Path.home() / ".privacy-guard" / "models" / "person-ner"
# Weight-only quantization keeps activations in full precision: unlike classic
# dynamic int8, it preserves this DeBERTa-v3 model's outputs (validated 10/10).
QUANT_BITS = 4
QUANT_BLOCK_SIZE = 32


class PersonScorer(torch.nn.Module):
    """Everything with weights, for one fixed question ("person").

    Inputs:  input_ids (1, T), word_positions (L,)  - first subword of each text word
    Outputs: count_logits (20,)                     - how many persons (argmax; 0 = none)
             span_scores (L, max_width)             - probability that words [i, i+w] are a person
    """

    def __init__(self, model: GLiNER2, prompt_position: int, label_position: int) -> None:
        super().__init__()
        self.model = model
        self.prompt_position = prompt_position
        self.label_position = label_position

    def forward(self, input_ids: torch.Tensor, word_positions: torch.Tensor):
        hidden = self.model.encoder(input_ids=input_ids, attention_mask=torch.ones_like(input_ids)).last_hidden_state[0]
        token_embs = hidden[word_positions]
        prompt_emb = hidden[self.prompt_position].unsqueeze(0)
        label_emb = hidden[self.label_position].unsqueeze(0)

        count_logits = self.model.count_pred(prompt_emb)[0]
        span_rep = self.model.span_rep(token_embs.unsqueeze(0), self._span_indices(token_embs))[0]  # (L, K, D)
        # The first counting step does not depend on the predicted count:
        # one step gives the projection used to score entities.
        label_proj = self.model.count_embed(label_emb, 1)[0, 0]  # (D,)
        span_scores = torch.sigmoid(torch.einsum("lkd,d->lk", span_rep, label_proj))
        return count_logits, span_scores

    def _span_indices(self, token_embs: torch.Tensor) -> torch.Tensor:
        """(start, end) word indices of every span of 1 to max_width words, as GLiNER2's
        compute_span_rep builds them. Rewritten from the tensor's size rather than len():
        len() is a plain int during export, which would freeze the text length in the graph."""
        max_width = self.model.max_width
        length = token_embs.size(0)
        starts = torch.arange(length).unsqueeze(1).expand(-1, max_width)
        ends = starts + torch.arange(max_width).unsqueeze(0)
        valid = ends < length
        spans = torch.stack([torch.where(valid, starts, 0), torch.where(valid, ends, 0)], dim=-1)
        return spans.reshape(1, -1, 2)


def capture_layout(model: GLiNER2) -> dict:
    """Reads the constant question prefix and marker positions from GLiNER2's own preprocessing."""
    collator = ExtractorCollator(model.processor, is_training=False, architecture=model.architecture)
    batch = collator([("x.", {"entities": {LABEL: ""}})])
    first_text_position = int(batch.text_word_indices[0][0])
    prompt_position, label_position = batch.schema_special_indices[0][0]
    return {
        "prefix_ids": batch.input_ids[0][:first_text_position].tolist(),
        "prompt_position": int(prompt_position),
        "label_position": int(label_position),
        "max_width": int(model.max_width),
        "threshold": 0.5,
        "source_model": MODEL_ID,
    }


def export(model: GLiNER2, layout: dict, path: Path) -> None:
    scorer = PersonScorer(model, layout["prompt_position"], layout["label_position"]).eval()
    input_ids = torch.tensor([layout["prefix_ids"] + [5, 6, 7, 8]])
    word_positions = torch.arange(len(layout["prefix_ids"]), input_ids.shape[1])
    with torch.no_grad():
        torch.onnx.export(
            scorer, (input_ids, word_positions), str(path),
            input_names=["input_ids", "word_positions"],
            output_names=["count_logits", "span_scores"],
            dynamic_axes={"input_ids": {1: "tokens"}, "word_positions": {0: "words"},
                          "span_scores": {0: "words"}},
            opset_version=17, dynamo=False,
        )


def quantize(source: Path, target: Path) -> None:
    config = DefaultWeightOnlyQuantConfig(
        block_size=QUANT_BLOCK_SIZE, is_symmetric=True, accuracy_level=4,
        bits=QUANT_BITS, op_types_to_quantize=("MatMul", "Gather"),
    )
    quantizer = MatMulNBitsQuantizer(onnx.load(str(source)), algo_config=config)
    quantizer.process()
    quantizer.model.save_model_to_file(str(target), use_external_data_format=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    with no_init_weights():
        model = GLiNER2.from_pretrained(MODEL_ID).eval()
    layout = capture_layout(model)

    full_precision = args.out / "model.fp32.onnx"
    export(model, layout, full_precision)
    quantize(full_precision, args.out / "model.onnx")
    full_precision.unlink()

    shutil.copyfile(Path(snapshot_download(MODEL_ID)) / "tokenizer.json", args.out / "tokenizer.json")
    (args.out / "config.json").write_text(json.dumps(layout, indent=2), encoding="utf-8")
    print(f"Name model written to {args.out}")


if __name__ == "__main__":
    main()
