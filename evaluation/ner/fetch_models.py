"""Fetch pinned evaluation artifacts; never install them into Privacy Guard."""

import json
import shutil
from pathlib import Path
from urllib.request import urlopen

from .fetch import BASE, sha256
from .license_policy import eligible_models


def remote_files(repo, revision):
    with urlopen(f"https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true", timeout=45) as response:
        return {item["rfilename"]: item for item in json.load(response)["siblings"]}


def download(repo, revision, filename, target, expected=None):
    if target.exists() and expected and sha256(target.read_bytes()) == expected:
        return
    temporary = target.with_suffix(target.suffix + ".download")
    target.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/{repo}/resolve/{revision}/{filename}"
    with urlopen(url, timeout=60) as response, temporary.open("wb") as stream:
        shutil.copyfileobj(response, stream, length=1 << 20)
    if expected and sha256(temporary.read_bytes()) != expected:
        raise ValueError("Downloaded model hash does not match its pinned LFS object")
    temporary.replace(target)
    print(f"Downloaded {target.parent.name}/{target.name} ({target.stat().st_size} bytes)", flush=True)


def main():
    from huggingface_hub import snapshot_download

    backbone_revision = "a0484667b22365f84929a935b5e50a51f71f159d"
    cache = BASE / "models/hf-cache/hub"
    snapshot_download("microsoft/mdeberta-v3-base", revision=backbone_revision, cache_dir=str(cache),
                      allow_patterns=["config.json", "tokenizer_config.json", "spm.model"])
    reference = cache / "models--microsoft--mdeberta-v3-base/refs/main"
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.write_text(backbone_revision, encoding="utf-8")
    plans = {
        "masker-mini": [("onnx/model_int4.onnx", "model.onnx"), ("config.json", "config.json"),
                        ("tokenizer.json", "tokenizer.json"), ("LICENSE", "LICENSE"), ("NOTICE", "NOTICE")],
        "nym-pii-multilingual-small": [("int8/model_int8.onnx", "model.onnx"), ("int8/tokenizer.json", "tokenizer.json"), ("int8/config.json", "config.json")],
        "distilcamembert-base-ner": [("model_quantized.onnx", "model.onnx"),
                                    ("model.onnx", "model_fp32.onnx"), ("config.json", "config.json"),
                                    ("sentencepiece.bpe.model", "sentencepiece.bpe.model"),
                                    ("tokenizer_config.json", "tokenizer_config.json")],
        "gliner_multi_pii-v1": [("pytorch_model.bin", "pytorch_model.bin"), ("gliner_config.json", "gliner_config.json")],
    }
    receipts = {}
    for model in eligible_models():
        name = model["id"]
        target = BASE / "models" / name
        if name == "gliner2-privacy-filter-PII-multi":
            origin = Path.home() / ".privacy-guard/models/person-ner"
            filenames = ["model.onnx", "config.json", "tokenizer.json"]
            if sha256((origin / "model.onnx").read_bytes()) != model["local_model_sha256"]:
                raise ValueError("Installed baseline weights differ from the selected artifact")
            target.mkdir(parents=True, exist_ok=True)
            for filename in filenames:
                shutil.copyfile(origin / filename, target / filename)
        elif name == "masker-mini" and (BASE.parents[1] / ".local-review/ner-evaluation/masker-mini/model_int4.onnx").exists():
            origin = BASE.parents[1] / ".local-review/ner-evaluation/masker-mini"
            if sha256((origin / "model_int4.onnx").read_bytes()) != model["local_model_sha256"]:
                raise ValueError("Masker weights differ from the selected artifact")
            target.mkdir(parents=True, exist_ok=True)
            for filename in ("config.json", "tokenizer.json", "LICENSE", "NOTICE"):
                shutil.copyfile(origin / filename, target / filename)
            shutil.copyfile(origin / "model_int4.onnx", target / "model.onnx")
        else:
            repo = model["source"].removeprefix("https://huggingface.co/")
            files = remote_files(repo, model["upstream_revision"])
            for source, filename in plans[name]:
                expected = files[source].get("lfs", {}).get("sha256")
                download(repo, model["upstream_revision"], source, target / filename, expected)
        if name == "distilcamembert-base-ner":
            from transformers import AutoTokenizer

            AutoTokenizer.from_pretrained(str(target), use_fast=True, local_files_only=True).save_pretrained(str(target))
        receipts[name] = {p.name: {"sha256": sha256(p.read_bytes()), "bytes": p.stat().st_size}
                          for p in target.iterdir() if p.is_file() and not p.name.endswith(".download")}
        print(f"Verified {name}", flush=True)
    (BASE / "models/artifacts.json").write_text(json.dumps(receipts, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
