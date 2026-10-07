"""Prepare a licensed, non-WikiNER subset of the published FENEC v1 corpus."""

import hashlib
import json
from collections import Counter
from urllib.request import urlopen

from .cohort import RUN_DIR
from .fetch import BASE, sha256

REVISION = "3a975635d57712096d8ebf859d842042c782837b"
ROOT = f"https://raw.githubusercontent.com/alicemillour/FENEC/{REVISION}/"
GROUPS = {
    "fenec-wikinews": ("CC-BY-2.5", ["information02-Wikinews"]),
    "fenec-gsd": ("CC-BY-SA-4.0", ["multi01-UDFrenchGSD"]),
    "fenec-republicain": ("CC-BY-SA-2.0", ["information03-LEstRepublicain"]),
    "fenec-rhapsodie": ("CC-BY-SA-4.0", [f"spoken{i:02}-Rhapsodie" for i in range(1, 4)]),
}


def read_gold(text, annotation):
    spans, labels = [], Counter()
    for line in annotation.splitlines():
        if not line.startswith("T"):
            continue
        _, bounds, value = line.split("\t", 2)
        kind, offsets = bounds.split(" ", 1)
        labels[kind] += 1
        if not kind.startswith("pers"):
            continue
        if ";" in offsets:
            raise ValueError("Discontinuous person annotation needs an explicit scorer")
        start, end = map(int, offsets.split())
        if text[start:end] != value:
            raise ValueError("BRAT offsets differ from the unmodified source text")
        spans.append({"kind": "PERSON", "start": start, "end": end, "source_label": kind})
    return spans, labels


def fetch_asset(path, tree):
    with urlopen(ROOT + path, timeout=45) as response:
        content = response.read()
    git_digest = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
    if git_digest != tree[path]:
        raise ValueError("FENEC asset differs from the pinned Git tree")
    target = BASE / "data/raw/fenec" / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return content.decode("utf-8"), {"local_path": f"fenec/{path}", "url": ROOT + path,
                                     "sha256": sha256(content), "bytes": len(content)}


def prepared_records(name):
    for document in GROUPS[name][1]:
        folder = BASE / "data/raw/fenec/FENEC"
        text = (folder / f"{document}.txt").read_bytes().decode("utf-8")
        annotation = (folder / f"{document}.ann").read_bytes().decode("utf-8")
        spans, _ = read_gold(text, annotation)
        yield {"id": f"{name}:{document}", "dataset": name, "split": "test", "text": text,
               "spans": spans, "source_tag_anomalies": {}, "source": f"FENEC/{document}.txt", "source_revision": REVISION}


def main():
    with urlopen(f"https://api.github.com/repos/alicemillour/FENEC/git/trees/{REVISION}?recursive=1", timeout=45) as response:
        tree = {item["path"]: item["sha"] for item in json.load(response)["tree"]}
    _, notice = fetch_asset("README.md", tree)
    manifest_path = BASE / "sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["datasets"] = [item for item in manifest["datasets"] if not item["id"].startswith("fenec-")]
    records, audit = [], {}
    for name, (license_name, documents) in GROUPS.items():
        assets, categories = [notice], Counter()
        for document in documents:
            text, receipt = fetch_asset(f"FENEC/{document}.txt", tree)
            assets.append(receipt)
            annotation, receipt = fetch_asset(f"FENEC/{document}.ann", tree)
            assets.append(receipt)
            spans, labels = read_gold(text, annotation)
            categories.update(labels)
            records.append({"id": f"{name}:{document}", "dataset": name, "split": "test",
                            "text": text, "spans": spans, "source_tag_anomalies": {},
                            "source": f"FENEC/{document}.txt", "source_revision": REVISION})
        manifest["datasets"].append({"id": name, "revision": REVISION, "origin": "https://github.com/alicemillour/FENEC",
            "license": license_name, "assets": assets, "commercial_evaluation": True,
            "evaluation_status": "active", "redistribute_with_product": False,
            "use": "Inference evaluation only; preserve data attribution and share-alike on redistributed derivatives"})
        audit[name] = {"documents": len(documents), "source_labels": dict(categories)}
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records)
    target = RUN_DIR / "independent.jsonl"
    if target.exists() and target.read_bytes() != payload.encode("utf-8"):
        raise ValueError("Refusing to alter the frozen independent corpus")
    target.write_text(payload, encoding="utf-8", newline="\n")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    result = {"revision": REVISION, "documents": len(records), "characters": sum(len(r["text"]) for r in records),
              "person_mentions": sum(len(r["spans"]) for r in records), "datasets": audit,
              "sha256": sha256(target.read_bytes()), "mapping": "All pers.* to PERSON; roles func.* excluded",
              "selection": "All six FENEC v1 non-WikiNER documents declaring CC BY or CC BY-SA in the source table",
              "exposure_note": "Different source from WikiNER; not a guarantee of absence from model pretraining"}
    (RUN_DIR / "independent-cohort.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
