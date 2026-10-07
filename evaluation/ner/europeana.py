"""Preserve contiguous source tokens in bounded IO chunks without splitting entities."""

from .tagged_text import convert


def read(path):
    rows = [line.rsplit(None, 1) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    tokens, tags, first, index = [], [], 0, 0
    for position, (token, tag) in enumerate(rows):
        tokens.append(token)
        tags.append(tag)
        if position + 1 != len(rows) and (len(tokens) < 128 or tag != "O"):
            continue
        text, spans, anomalies = convert(tokens, tags, scheme="IO")
        yield {"id": f"europeana-newspapers-fr:{index}", "dataset": "europeana-newspapers-fr",
               "domain": "historical-newspaper-OCR", "group": f"source-token-block:{first // 2048}",
               "split": "test", "language": "fr", "text": text, "spans": spans,
               "source_token_start": first, "source_token_end": position + 1,
               "token_count": len(tokens), "source_tag_scheme": "IO",
               "whitespace": "single_space_between_source_tokens", "source_tag_anomalies": anomalies}
        tokens, tags, first, index = [], [], position + 1, index + 1
