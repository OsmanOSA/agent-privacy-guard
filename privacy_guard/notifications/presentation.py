"""Document, protected occurrence counts, then grouping metadata.

Adapted from Driftlight's message hierarchy; only existing allowed summary
metadata enters the display. Windows retains ownership of native layout.
"""

from privacy_guard.protection_summary import REDUCED_TEXT, ProtectionSummary, describe_counts

TITLE = "Privacy Guard"
TEXT_LIMIT = 510  # Bytes in the native 255 UTF-16-unit body limit.


def card_content(batch):
    """Structured display fields contain only the existing allowed summary."""
    documents = [ProtectionSummary({}, value).record()["document"] for value in batch["documents"]]
    documents = [value for value in documents if value]
    subject = documents[0] if len(documents) == 1 else (
        f"{len(documents)} fichiers" + (" ou plus" if len(documents) >= 3 else "")) if documents else "Résultat d’outil"
    parts = [describe_counts(batch["counts"][action], verb) + "." for action, verb in (
        ("pseudonymized", "pseudonymisé"), ("redacted", "masqué")) if batch["counts"][action]]
    # Only an allowlisted reason enters the display (protection_summary.REDUCED_TEXT).
    reduced = REDUCED_TEXT.get(batch.get("reduced"))
    if reduced:
        parts.append(reduced[:1].upper() + reduced[1:] + ".")
    has_personal = bool(batch["counts"]["pseudonymized"])
    has_redaction = bool(batch["counts"]["redacted"])
    headline = "Protection réduite" if reduced else "Protection appliquée" if has_personal and has_redaction else (
        "Pseudonymisation appliquée" if has_personal else "Masquage appliqué")
    footer = f"{batch['events']} traitements regroupés." if batch["events"] > 1 else "Traitement local"
    return {"document": subject, "headline": headline, "details": "\n".join(parts), "footer": footer}


def banner_text(batch):
    content = card_content(batch)
    subject = content["document"]
    lines = [subject, content["details"]]
    if batch["events"] > 1:
        lines.append(content["footer"])
    text = "\n".join(lines)
    if len(text.encode("utf-16-le")) > TEXT_LIMIT:
        totals = [f"{sum(batch['counts'][action].values())} occurrences {verb}" for action, verb in (
            ("pseudonymized", "pseudonymisées"), ("redacted", "masquées")) if batch["counts"][action]]
        if batch.get("reduced") in REDUCED_TEXT:
            totals.append("détection des noms réduite")
        short_subject = subject if len(subject) <= 36 else subject[:23] + "…" + subject[-12:]
        text = short_subject + "\n" + "; ".join(totals) + ". Détails dans Claude Code."
    return text


def example_batch():
    """The CLI preview uses the production presentation with synthetic counts."""
    return {"origin": None, "events": 1, "documents": ["document-exemple.md"],
            "counts": {"pseudonymized": {"person_name": 3, "email": 4}, "redacted": {}}}
