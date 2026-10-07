"""Read typed PARSEME-FR entities against the original Sequoia sentence text."""

import re
from collections import defaultdict


def token_offsets(text, rows):
    offsets, cursor, ranges = {}, 0, {}
    for row in rows:
        identifier, form = row[:2]
        if "-" in identifier:
            first, last = map(int, identifier.split("-"))
        elif "." in identifier:
            continue
        else:
            first = last = int(identifier)
            if first in ranges:
                offsets[first] = ranges[first]
                continue
        start = text.find(form, cursor)
        if start < 0 or text[cursor:start].strip():
            raise ValueError(f"Source token alignment failed at token {identifier}")
        end = start + len(form)
        if first != last:
            ranges.update({index: (start, end) for index in range(first, last + 1)})
        else:
            offsets[first] = (start, end)
        cursor = end
    if text[cursor:].strip():
        raise ValueError("Unaligned source text suffix")
    return offsets


def parse_block(block):
    lines = block.splitlines()
    metadata = dict(line[2:].split(" = ", 1) for line in lines if line.startswith("# ") and " = " in line)
    identifier = metadata.get("sent_id")
    if identifier is None or identifier.startswith("frwiki_50.1000"):
        return None
    text = metadata["text"]
    rows = [line.split("\t") for line in lines if line and not line.startswith("#")]
    offsets = token_offsets(text, rows)
    entities = defaultdict(lambda: {"tokens": [], "label": None})
    for row in rows:
        if not row[0].isdigit():
            continue
        for mark in row[10].split(";"):
            if mark == "*":
                continue
            entity_id, _, label = mark.partition(":")
            entities[entity_id]["tokens"].append(int(row[0]))
            if label:
                entities[entity_id]["label"] = label
    spans = []
    for entity in entities.values():
        if "NE-PERS." not in str(entity["label"]):
            continue
        ids = sorted(entity["tokens"])
        if ids != list(range(ids[0], ids[-1] + 1)):
            raise ValueError("Discontinuous PERSON reference needs a segment-aware task")
        spans.append({"kind": "PERSON", "start": offsets[ids[0]][0],
                      "end": offsets[ids[-1]][1], "source_label": entity["label"]})
    return {"id": f"deep-sequoia-nonwiki:{identifier}", "dataset": "deep-sequoia-nonwiki",
            "domain": re.sub(r"_\d+$", "", identifier), "group": re.sub(r"_\d+$", "", identifier),
            "text": text, "spans": spans, "split": "test", "language": "fr"}


def read(path, exclusions):
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8")):
        try:
            row = parse_block(block)
        except ValueError as error:
            identifier = re.search(r"# sent_id = (.+)", block).group(1)
            exclusions.append({"dataset": "deep-sequoia-nonwiki", "source_id": identifier,
                               "reason": str(error)})
            continue
        if row is not None:
            yield row
