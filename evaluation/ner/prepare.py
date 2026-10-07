"""Normalize pinned gold corpora and produce a content-free annotation audit."""

import hashlib
import json
from collections import Counter

from .fetch import BASE, sha256
from .readers import hipe, wikiner
from .license_policy import eligible_datasets
from .fenec import GROUPS, prepared_records


def verify_assets():
    for dataset in eligible_datasets():
        for asset in dataset["assets"]:
            path = BASE / "data" / "raw" / asset["local_path"]
            if sha256(path.read_bytes()) != asset["sha256"]:
                raise ValueError(f"Dataset integrity failure: {asset['local_path']}")


def prepare_dataset(name, records):
    destination = BASE / "data" / "prepared" / f"{name}.jsonl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    counts, entities, anomalies = Counter(), Counter(), Counter()
    fingerprints, duplicates, conflicting, partial = {}, 0, 0, 0
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        for row in records:
            text = row["text"]
            for span in row["spans"]:
                if not 0 <= span["start"] < span["end"] <= len(text):
                    raise ValueError(f"Invalid gold offsets in {row['id']}")
                entities[f"{row['split']}:{span['kind']}"] += 1
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            signature = (row["split"], json.dumps(row["spans"], sort_keys=True))
            if digest in fingerprints:
                previous = fingerprints[digest]
                duplicates += 1
                conflicting += previous[1] != signature[1]
                if previous[0] != signature[0]:
                    raise ValueError("Identical input occurs in calibration and test")
            fingerprints[digest] = signature
            counts[row["split"]] += 1
            partial += row.get("partial_annotation_tokens", 0)
            anomalies.update(row["source_tag_anomalies"])
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    temporary.replace(destination)
    return {"records": dict(counts), "entities": dict(entities),
            "source_tag_anomalies": dict(anomalies), "duplicate_inputs": duplicates,
            "duplicate_inputs_with_conflicting_annotations": conflicting,
            "partial_annotation_tokens": partial, "prepared_sha256": sha256(destination.read_bytes())}


def main():
    verify_assets()
    raw = BASE / "data" / "raw"
    readers = {"wikiner-fr-gold": lambda: wikiner(raw / "wikiner-fr-gold/corpus.conll"),
               "hipe2022-fr": lambda: iter_hipe(raw)}
    readers.update({name: lambda name=name: prepared_records(name) for name in GROUPS})
    from .additional_cohort import TASKS

    delegated = [dataset["id"] for dataset in eligible_datasets() if dataset["id"] in TASKS]
    datasets = {dataset["id"]: prepare_dataset(dataset["id"], readers[dataset["id"]]())
                for dataset in eligible_datasets() if dataset["id"] not in TASKS}
    report = {"schema_version": 1, "datasets": datasets,
              "delegated_to_evaluation.ner.additional_cohort": delegated}
    target = BASE / "results" / "dataset-audit.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def iter_hipe(raw):
    yield from hipe(raw / "hipe2022-fr/dev.tsv", "calibration")
    yield from hipe(raw / "hipe2022-fr/test.tsv", "test")


if __name__ == "__main__":
    main()
