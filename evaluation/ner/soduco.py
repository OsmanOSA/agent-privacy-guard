"""Recover nested human reference offsets; never relabel businesses as persons."""

import json
import re

KINDS = {"PER": "NAME_OR_BUSINESS", "SPAT": "ADDRESS", "LOC": "STREET", "CARDINAL": "STREET_NUMBER"}


def xml_spans(xml):
    parts, spans, stack, cursor, previous = [], [], [], 0, 0
    for tag in re.finditer(r"<(\/?)([A-Z-]+)>", xml):
        content = xml[previous:tag.start()].replace("\u2029", "\n")
        parts.append(content)
        cursor += len(content)
        closing, label = tag.groups()
        if closing:
            opening, start = stack.pop()
            if opening != label:
                raise ValueError("Unbalanced source annotation XML")
            if label in KINDS:
                spans.append({"kind": KINDS[label], "start": start, "end": cursor, "source_label": label})
        else:
            stack.append((label, cursor))
        previous = tag.end()
    if stack:
        raise ValueError("Unclosed source XML annotation")
    parts.append(xml[previous:].replace("\u2029", "\n"))
    return "".join(parts), sorted(spans, key=lambda span: (span["start"], span["end"], span["kind"]))


def read(path, exclusions):
    for source in json.loads(path.read_text(encoding="utf-8")):
        identifier = f"{source['book']}:{source['page']}:{source['id']}"
        text, spans = xml_spans(source["nested_ner_xml_ref"])
        if text != source["text_ocr_ref"]:
            exclusions.append({"dataset": "soduco-nested-ner", "source_id": identifier,
                               "reason": "Annotated XML text differs from corrected reference text"})
            continue
        yield {"id": f"soduco-nested-ner:{identifier}", "dataset": "soduco-nested-ner",
               "domain": source["book"], "group": f"{source['book']}:{source['page']}",
               "split": "test", "language": "fr", "text": text, "spans": spans,
               "valid_paired_ocr": source["has_valid_ner_xml_pero"]}
