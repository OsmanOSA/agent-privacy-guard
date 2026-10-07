"""Convert source tokens and BIO/BIOES labels to explicit character spans."""

from collections import Counter

ALIASES = {"PER": "PERSON", "pers": "PERSON", "LOC": "LOCATION", "loc": "LOCATION",
           "ORG": "ORGANIZATION", "org": "ORGANIZATION", "MISC": "MISC",
           "time": "TIME", "prod": "PRODUCT"}


def convert(tokens, tags, separators=None, scheme="BIO"):
    if len(tokens) != len(tags):
        raise ValueError("Tokens and labels must be aligned")
    separators = separators or [" "] * len(tokens)
    parts, positions, cursor = [], [], 0
    for index, token in enumerate(tokens):
        parts.append(token)
        positions.append((cursor, cursor + len(token)))
        cursor += len(token)
        if index < len(tokens) - 1:
            parts.append(separators[index])
            cursor += len(separators[index])
    text, spans, active, anomalies = "".join(parts), [], None, Counter()
    bioes = scheme == "BIOES"

    def close(ended=False):
        nonlocal active
        if active is not None:
            if bioes and not ended:
                anomalies[f"unclosed_bioes_entity:{active['kind']}"] += 1
            spans.append(active)
            active = None

    for tag, (start, end) in zip(tags, positions):
        if tag == "O":
            close()
            continue
        prefix, source_kind = tag.split("-", 1)
        if prefix not in {"B", "I", "E", "S"} or source_kind not in ALIASES:
            raise ValueError(f"Unsupported source tag: {tag}")
        kind = ALIASES[source_kind]
        if prefix in {"B", "S"}:
            close()
            active = {"kind": kind, "start": start, "end": end}
        elif active is not None and active["kind"] == kind:
            active["end"] = end
        else:
            close()
            if scheme != "IO":
                anomalies["orphan_continuation"] += 1
            active = {"kind": kind, "start": start, "end": end}
        if prefix in {"E", "S"}:
            close(ended=True)
    close()
    return text, spans, dict(anomalies)
