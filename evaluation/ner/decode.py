"""Decode native BIO/BIOES predictions and apply a fixed person-fragment rule."""


def merge_person_spans(text, spans):
    merged = []
    for span in sorted(spans, key=lambda s: (s["start"], s["end"])):
        start, end = span["start"], span["end"]
        while start < end and text[start].isspace():
            start += 1
        while start < end and text[end - 1].isspace():
            end -= 1
        if start == end:
            continue
        if merged and (start <= merged[-1]["end"] or text[merged[-1]["end"]:start].isspace()):
            merged[-1]["end"] = max(merged[-1]["end"], end)
        else:
            merged.append({"kind": "PERSON", "start": start, "end": end})
    return merged


def decode(text, raw, threshold):
    if raw["encoding"] == "spans":
        return merge_person_spans(text, [item for item in raw["items"] if item["score"] >= threshold])
    spans = []
    for window in raw["windows"]:
        active, previous_kind = None, None
        for token in window:
            label = token["label"]
            if token["score"] < threshold or label == "O":
                active, previous_kind = None, None
                continue
            prefix, kind = label.split("-", 1)
            if kind not in {"PER", "PERSON", "GIVEN_NAME", "SURNAME"}:
                active, previous_kind = None, None
                continue
            if active is not None and previous_kind == kind and prefix in {"I", "E"}:
                active["end"] = token["end"]
            else:
                active = {"kind": "PERSON", "start": token["start"], "end": token["end"]}
                spans.append(active)
            previous_kind = kind
            if prefix in {"E", "S"}:
                active, previous_kind = None, None
    return merge_person_spans(text, spans)
