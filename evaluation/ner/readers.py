"""Read public corpus annotations without inventing text or entity labels."""

import hashlib

from .tagged_text import convert


def record(identifier, dataset, split, tokens, tags, **metadata):
    separators = metadata.pop("separators", None)
    text, spans, anomalies = convert(tokens, tags, separators, metadata["source_tag_scheme"])
    return {"id": identifier, "dataset": dataset, "split": split, "language": "fr",
            "text": text, "spans": spans, "source_tag_anomalies": anomalies, **metadata}


def wikiner(path):
    tokens, tags, index = [], [], 0
    for line in path.read_text(encoding="utf-8-sig").splitlines() + [""]:
        if line.strip():
            token, _pos, tag = line.split()
            tokens.append(token)
            tags.append(tag)
        elif tokens:
            # Identical input sentences stay together regardless of their source row.
            digest = hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest()
            split = "calibration" if int(digest, 16) % 10 == 0 else "test"
            yield record(f"wikiner-fr-gold:{index}", "wikiner-fr-gold", split,
                         tokens, tags, source_row=index, token_count=len(tokens),
                         text_sha256=digest, source_tag_scheme="BIOES",
                         whitespace="single_space_between_source_tokens")
            tokens, tags, index = [], [], index + 1


def hipe(path, split):
    columns, tokens, tags, separators = None, [], [], []
    document, partial_tokens, index = None, 0, 0
    for line in path.read_text(encoding="utf-8-sig").splitlines() + [""]:
        if line.startswith("#"):
            if line.startswith("# hipe2022:document_id ="):
                document = line.split("=", 1)[1].strip()
            continue
        if not line:
            if tokens:
                yield record(f"hipe2022-fr:{split}:{index}", "hipe2022-fr", split,
                             tokens, tags, separators=separators, source_document=document,
                             token_count=len(tokens), source_tag_scheme="BIO",
                             partial_annotation_tokens=partial_tokens,
                             whitespace="hipe_NoSpaceAfter_and_EndOfLine")
                tokens, tags, separators, partial_tokens = [], [], [], 0
                index += 1
            continue
        fields = line.split("\t")
        if columns is None:
            columns = fields
            continue
        if len(fields) != len(columns):
            raise ValueError("Unexpected HIPE column count")
        row = dict(zip(columns, fields))
        misc = row["MISC"].split("|")
        tokens.append(row["TOKEN"])
        tags.append(row["NE-COARSE-LIT"])
        separators.append("" if "NoSpaceAfter" in misc else "\n" if "EndOfLine" in misc else " ")
        partial_tokens += any(flag.startswith("Partial-") for flag in misc)
