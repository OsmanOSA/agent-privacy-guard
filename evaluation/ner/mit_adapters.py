"""Native CPU deployments for the three pinned MIT candidates."""

import json

from .fetch import BASE
from .mit_token_model import NativeTokenModel


class SpacyModel:
    def __init__(self, directory):
        import spacy

        spacy.require_cpu()
        self.model = spacy.load(directory)
        self.backend = "spaCy 3.8 CPU; xx_ent_wiki_sm 3.8.0 native NER"

    def raw(self, text):
        document = self.model(text)
        return {"encoding": "spans", "items": [{"start": ent.start_char, "end": ent.end_char,
            "score": 1.0} for ent in document.ents if ent.label_ == "PER"]}


class TorchSession:
    def __init__(self, model):
        self.model = model

    def run(self, outputs, feed):
        import torch

        with torch.inference_mode():
            logits = self.model(**{name: torch.from_numpy(array) for name, array in feed.items()}).logits
        return [logits.numpy()]


class ModernModel(NativeTokenModel):
    def __init__(self, directory):
        from tokenizers import Tokenizer
        from transformers import AutoConfig, AutoModelForTokenClassification

        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.no_padding()
        self.tokenizer.enable_truncation(max_length=512, stride=64)
        config = AutoConfig.from_pretrained(directory, local_files_only=True)
        config.reference_compile = False
        # This checkpoint uses IO labels (PER, LOC...), not BIO. Preserve its
        # contiguous spans by supplying the decoder's equivalent I- labels.
        self.labels = {str(key): "O" if value == "O" else f"I-{value}"
                       for key, value in config.id2label.items()}
        model = AutoModelForTokenClassification.from_pretrained(directory, config=config,
            local_files_only=True, attn_implementation="eager").eval()
        self.session = TorchSession(model)
        self.inputs = {"input_ids", "attention_mask"}
        self.backend = "PyTorch CPU FP32 eager; ModernCamemBERT; complete 512-token windows, stride 64"


class HmbertModel:
    def __init__(self, directory):
        import flair
        import torch
        from flair.models import SequenceTagger

        flair.device = torch.device("cpu")
        self.model = SequenceTagger.load(str(directory / "pytorch_model.bin")).eval()
        self.backend = "Flair 0.15.1 PyTorch CPU FP32; published hmBERT Tiny French NER"

    def raw(self, text):
        from flair.data import Sentence

        sentence = Sentence(text)
        covered = {index for token in sentence for index in range(token.start_position, token.end_position)}
        required = {index for index, char in enumerate(text) if not char.isspace()}
        if required - covered:
            raise ValueError("Flair source tokenizer omitted non-whitespace characters")
        self.model.predict(sentence, mini_batch_size=1, embedding_storage_mode="none")
        return {"encoding": "spans", "items": [{"start": span.start_position, "end": span.end_position,
            "score": float(span.score)} for span in sentence.get_spans("ner") if span.tag == "PER"]}


def load_model(name, threads=4):
    import torch

    candidates = json.loads((BASE / "mit-candidates.json").read_text(encoding="utf-8"))["models"]
    if name not in {item["id"] for item in candidates if item["license"] == "MIT"}:
        raise ValueError("Candidate is outside the pinned MIT registry")
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    constructors = {"spacy-multilingual": SpacyModel, "hmbert-tiny-fr": HmbertModel,
                    "moderncamembert-fr": ModernModel}
    return constructors[name](BASE / "models" / name)
