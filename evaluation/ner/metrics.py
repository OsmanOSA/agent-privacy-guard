"""Measure exact entities, complete mention coverage and character coverage."""

from collections import Counter


def validate_spans(text, spans):
    for span in spans:
        start, end = span["start"], span["end"]
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError("Invalid prediction character offsets")
        if not isinstance(span["kind"], str):
            raise ValueError("Entity kind must be a string")


def character_positions(text, spans):
    return {index for span in spans for index in range(span["start"], span["end"])
            if not text[index].isspace()}


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


class Metrics:
    def __init__(self):
        self.counts = Counter()

    def add(self, text, gold, predicted):
        validate_spans(text, gold)
        validate_spans(text, predicted)
        expected = {(s["kind"], s["start"], s["end"]) for s in gold}
        found = {(s["kind"], s["start"], s["end"]) for s in predicted}
        gold_characters = character_positions(text, gold)
        predicted_characters = character_positions(text, predicted)
        self.counts.update({"records": 1, "gold_entities": len(expected),
                            "predicted_entities": len(found), "exact_true_positives": len(expected & found),
                            "gold_characters": len(gold_characters),
                            "predicted_characters": len(predicted_characters),
                            "covered_gold_characters": len(gold_characters & predicted_characters),
                            "negative_records": int(not gold),
                            "negative_records_with_predictions": int(not gold and bool(predicted))})
        for span in gold:
            relevant = [p for p in predicted if p["kind"] == span["kind"]]
            positions = character_positions(text, [span])
            if positions and positions <= character_positions(text, relevant):
                self.counts["fully_covered_entities"] += 1

    def report(self):
        c = self.counts
        precision = ratio(c["exact_true_positives"], c["predicted_entities"])
        recall = ratio(c["exact_true_positives"], c["gold_entities"])
        f1 = ratio(2 * c["exact_true_positives"], c["gold_entities"] + c["predicted_entities"])
        return {**dict(c), "exact_precision": precision, "exact_recall": recall, "exact_f1": f1,
                "full_entity_coverage": ratio(c["fully_covered_entities"], c["gold_entities"]),
                "character_recall": ratio(c["covered_gold_characters"], c["gold_characters"]),
                "character_precision": ratio(c["covered_gold_characters"], c["predicted_characters"]),
                "negative_record_false_positive_rate": ratio(c["negative_records_with_predictions"], c["negative_records"])}
