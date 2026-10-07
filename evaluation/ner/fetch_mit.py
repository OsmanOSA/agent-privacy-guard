"""Fetch pinned MIT candidates into ignored local evaluation storage."""

import json
import shutil
import zipfile
from urllib.request import urlopen

from .fetch import BASE, sha256
from .fetch_models import download, remote_files


def main():
    registry = json.loads((BASE / "mit-candidates.json").read_text(encoding="utf-8"))
    receipts = {}
    for candidate in registry["models"]:
        name, revision = candidate["id"], candidate["revision"]
        directory = BASE / "models" / name
        directory.mkdir(parents=True, exist_ok=True)
        if name == "spacy-multilingual":
            wheel = directory / "xx_ent_wiki_sm-3.8.0-py3-none-any.whl"
            url = f"https://github.com/explosion/spacy-models/releases/download/{revision}/{wheel.name}"
            if not wheel.exists():
                with urlopen(url, timeout=60) as response, wheel.open("wb") as stream:
                    shutil.copyfileobj(response, stream)
            with zipfile.ZipFile(wheel) as archive:
                root = "xx_ent_wiki_sm/xx_ent_wiki_sm-3.8.0/"
                for item in archive.infolist():
                    if item.filename.startswith(root) and not item.is_dir():
                        target = directory / item.filename.removeprefix(root)
                        if ".." in target.relative_to(directory).parts:
                            raise ValueError("Unsafe model archive member")
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(archive.read(item))
            metadata = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
            if metadata["license"] != "MIT" or metadata["version"] != "3.8.0":
                raise ValueError("Unexpected spaCy license or version")
        else:
            repo = candidate["source"].removeprefix("https://huggingface.co/")
            files = remote_files(repo, revision)
            names = ["README.md", "pytorch_model.bin"] if name == "hmbert-tiny-fr" else [
                "README.md", "config.json", "model.safetensors", "tokenizer.json",
                "tokenizer_config.json", "special_tokens_map.json"]
            for filename in names:
                download(repo, revision, filename, directory / filename,
                         files[filename].get("lfs", {}).get("sha256"))
            if "license: mit" not in (directory / "README.md").read_text(encoding="utf-8"):
                raise ValueError("Pinned card does not declare MIT")
        receipts[name] = {str(p.relative_to(directory)): {"sha256": sha256(p.read_bytes()),
            "bytes": p.stat().st_size} for p in directory.rglob("*") if p.is_file()}
        print(f"Verified {name}", flush=True)
    (BASE / "mit-artifacts.json").write_text(json.dumps(receipts, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
