"""Freeze three public reference corpora before any model prediction."""

import hashlib
import json
import tarfile
from collections import Counter

from . import europeana, sequoia, soduco
from .fetch import BASE, sha256
from .metrics import validate_spans

RUN = BASE / "results" / "additional-20261006-v2"
RAW = BASE / "data" / "raw" / "additional-20261006"
SEED = "additional-french-reference-20261006-v2"
TASKS = {"deep-sequoia-nonwiki": "PERSON", "europeana-newspapers-fr": "PERSON",
         "soduco-nested-ner": "NAME_OR_BUSINESS"}


def order(rows, purpose):
    return sorted(rows, key=lambda row: sha256(f"{SEED}:{purpose}:{row['id']}".encode()))


def write_frozen(path, rows):
    content = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    if path.exists() and path.read_text(encoding="utf-8") != content:
        raise ValueError(f"Frozen corpus cannot be replaced: {path.name}")
    path.write_text(content, encoding="utf-8", newline="\n")
    return sha256(path.read_bytes())


def main():
    manifest = json.loads((BASE / "additional-datasets.json").read_text(encoding="utf-8"))
    for dataset in manifest["datasets"]:
        if dataset["id"] not in TASKS:
            continue
        if dataset["commercial_evaluation"] is not True:
            raise ValueError("Source not eligible for local evaluation")
        for asset in dataset["assets"]:
            if sha256((RAW / asset["file"]).read_bytes()) != asset["sha256"]:
                raise ValueError("Source integrity failure")
    exclusions = []
    with tarfile.open(RAW / "sequoia-9.2.tgz", "r:gz") as archive:
        source = archive.extractfile("sequoia-9.2/sequoia-ud.parseme.frsemcor").read()
        extracted = RAW / "sequoia-ud.parseme.frsemcor"
        if not extracted.exists():
            extracted.write_bytes(source)
        if source != extracted.read_bytes():
            raise ValueError("Extracted Sequoia differs from verified official archive")
    corpora = {"deep-sequoia-nonwiki": list(sequoia.read(RAW / "sequoia-ud.parseme.frsemcor", exclusions)),
               "europeana-newspapers-fr": list(europeana.read(RAW / "europeana.bio")),
               "soduco-nested-ner": list(soduco.read(RAW / "soduco.json", exclusions))}
    RUN.mkdir(parents=True, exist_ok=True)
    report = {"seed": SEED, "tasks": TASKS, "exclusions": exclusions, "datasets": {},
              "thresholds": "Transferred unchanged from comparison-20261005 WikiNER calibration",
              "timing_passes": 3, "timing_inputs_per_dataset": 75, "cpu_threads": 4}
    old = BASE / "results/comparison-20261005/independent.jsonl"
    control_texts = {json.loads(line)["text"] for line in old.read_text(encoding="utf-8").splitlines()}
    for name, rows in corpora.items():
        seen, unique = set(), []
        for row in rows:
            validate_spans(row["text"], row["spans"])
            digest = hashlib.sha256(row["text"].encode()).hexdigest()
            if digest in seen or row["text"] in control_texts:
                exclusions.append({"dataset": name, "source_id": row["id"], "reason": "Exact duplicate input"})
                continue
            seen.add(digest)
            row["text_sha256"] = digest
            unique.append(row)
        selected = order(unique, "quality")[:512] if name != "deep-sequoia-nonwiki" else unique
        timing = order(selected, "timing")[:75]
        gold = [span for row in selected for span in row["spans"] if span["kind"] == TASKS[name]]
        report["datasets"][name] = {"available_records": len(unique), "selected_records": len(selected),
            "gold_entities": len(gold), "negative_records": sum(not any(s["kind"] == TASKS[name] for s in r["spans"]) for r in selected),
            "domains": dict(Counter(row["domain"] for row in selected)),
            "groups": len({row["group"] for row in selected}),
            "quality_sha256": write_frozen(RUN / f"{name}.jsonl", selected),
            "timing_sha256": write_frozen(RUN / f"{name}.timing.jsonl", timing)}
    (RUN / "cohort.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
