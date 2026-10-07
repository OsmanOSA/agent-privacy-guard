"""Write the content-free additional-corpus report from validated measurements."""

import json

from .fetch import BASE

NAMES = {"gliner2-privacy-filter-PII-multi": "GLiNER2 current INT4 export", "masker-mini": "Masker Mini INT4",
         "nym-pii-multilingual-small": "Nym small compressed export", "distilcamembert-base-ner": "DistilCamemBERT FP32",
         "gliner_multi_pii-v1": "GLiNER multilingual v1 FP32"}
DATASETS = {"deep-sequoia-nonwiki": "Deep Sequoia outside Wikipedia", "europeana-newspapers-fr": "Europeana French OCR",
            "soduco-nested-ner": "SoDUCo name-or-business diagnostic"}


def percent(value):
    return "undefined" if value is None else f"{100 * value:.2f}"


def main():
    summary = json.loads((BASE / "summary-additional-20261006.json").read_text(encoding="utf-8"))
    models, cohort, run = summary["models"], summary["cohort"], summary["run"]
    best = max(models, key=lambda name: models[name]["datasets"]["deep-sequoia-nonwiki"]["quality"]["exact_f1"])
    lines = ["# Additional French reference evaluation", "",
        f"{NAMES[best]} has the highest exact PERSON F1 on the retained non-Wikipedia Sequoia sentences in this run. The corpus-specific tables below compare the same five deployments against published human reference annotations. These are transferred-threshold measurements, with no new fine-tuning or calibration.", "",
        "Sequoia and Europeana evaluate PERSON with different reference conventions. SoDUCo evaluates coverage of its broader name-or-business references by the same person-only outputs. Its diagnostic score is not a person-only leaderboard. No address inference score is reported.", "",
        "## Inputs and reference annotations", "",
        "| Corpus | Inputs | Reference target | Gold mentions | Negative inputs |",
        "| --- | --- | --- | --- | --- |"]
    for dataset, title in DATASETS.items():
        item = cohort["datasets"][dataset]
        lines.append(f"| {title} | {item['selected_records']} | {cohort['tasks'][dataset]} | {item['gold_entities']} | {item['negative_records']} |")
    lines += ["", "All eligible non-Wikipedia Sequoia sentences were retained after documented exclusions and exact deduplication. Europeana and SoDUCo each use 512 records selected by a SHA-256 seed before inference. Each corpus has 75 common timing inputs and three shuffled timing passes, giving 225 timed observations per deployment per corpus.", "",
        "A reference is a text plus the expected category and character boundaries for every annotated occurrence. Exact precision, recall and F1 require matching both boundaries and category. Full coverage requires all non-whitespace characters of a reference mention, including punctuation, to be covered. Pooled scores below are micro scores; no incompatible corpus scores are pooled together.", ""]
    for dataset, title in DATASETS.items():
        lines += [f"## {title}", "",
            "| Deployment | Threshold | Precision % | Recall % | F1 % [95% interval] | Fully covered / gold | Partial | Entirely missed | Negative FP % |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for name, model in models.items():
            item = model["datasets"][dataset]
            q, misses, confidence = item["quality"], item["misses"], item["confidence"]["exact_f1_95"]
            lines.append(f"| {NAMES[name]} | {model['threshold']} | {percent(q['exact_precision'])} | {percent(q['exact_recall'])} | {percent(q['exact_f1'])} [{percent(confidence[0])}–{percent(confidence[1])}] | {q.get('fully_covered_entities', 0)}/{q['gold_entities']} | {misses.get('partial', 0)} | {misses.get('entirely_missed', 0)} | {percent(q['negative_record_false_positive_rate'])} |")
        lines += ["", "| Deployment | Warm median ms | Warm p95 ms | Observations |",
                  "| --- | --- | --- | --- |"]
        for name, model in models.items():
            timing = model["datasets"][dataset]["latency_ms"]
            lines.append(f"| {NAMES[name]} | {timing['p50']:.2f} | {timing['p95']:.2f} | {timing['observations']} |")
        lines.append("")
    lines += ["## Reference and interpretation limits", "",
        "[Deep Sequoia 9.2](https://deep-sequoia.inria.fr/) uses the typed PARSEME-FR NE layer in column 11, aligned with original sentence text. Noun supersenses are ignored. All 996 Wikipedia sentences are excluded; one sentence with a discontinuous PERSON annotation is excluded as a whole because this task requires continuous spans. Eighteen repeated source sentences are deduplicated. The retained set contains 270 PERSON references, with separate source-domain counts and scores in the JSON summary. Its medical sections are negative-heavy.", "",
        "[Europeana Newspapers](https://github.com/EuropeanaNewspapers/ner-corpora) supplies human labels in an IO export. Its 205,916 source token rows include two literal hash-sign tokens, not metadata comments. The reader partitions contiguous source tokens into chunks of at least 128 tokens, ending outside entities, and joins tokens with spaces. Original newspaper whitespace and article boundaries are unavailable in this export. Exact F1 therefore uses IO-derived contiguous spans; adjacent same-category entities cannot be separated reliably. The authors also warn about OCR and removed noisy sentence fragments. Treat this result as an OCR stress test.", "",
        "[SoDUCo v2](https://zenodo.org/records/8167628) has aligned text and human nested XML references. Three inconsistent text/XML records and eight repeated texts are excluded before sampling. The [authors' label definition](https://arxiv.org/html/2302.10204) combines people and businesses in PER. Person-only predictions are relabeled NAME_OR_BUSINESS for this diagnostic comparison; this does not change their detected spans or make them business detectors. The full prepared references preserve ADDRESS, STREET and STREET_NUMBER. Those categories await compatible inference outputs before scoring. The selected entries all contain a name-or-business reference, so negative-input false-positive rate is undefined.", "",
        "AjMC is held aside. No invented text, generated names or model-created reference annotations enter these cohorts. Different sources remove dependence on the WikiNER evaluation partition, but undisclosed training or pretraining exposure remains possible.", "",
        "Intervals use 1,000 paired bootstrap resamples: Sequoia sentences, Europeana source-token blocks and SoDUCo source pages. Sequoia sentence intervals do not account for article-level dependence because original article groups are not reconstructed. Europeana blocks approximate local dependence rather than known documents. Intervals describe sample uncertainty, not absence of training exposure or annotation errors.", "",
        "## Execution and reproducibility", "",
        f"Run: {run['started_at']} to {run['finished_at']}. CPU only, batch size one, four intra-operation threads, isolated sequential processes. Model artifacts and the decoding rules are unchanged from the initial comparison. Timing includes tokenization, all inference windows and decoding, after warm-up; excludes scoring, model loading and the full hook workflow. Model order rotates between passes. Background workload and power state are not controlled.", "",
        "Every saved quality score was recomputed from its predictions and reference inputs. All timing IDs and prediction hashes match the corresponding quality run. Parser tests verify source alignment, preservation of nested references and source tokens, an identity-reference F1 of 1, and rejection of shifted boundaries as exact matches. Raw text, reference surfaces, weights and predictions stay in ignored local folders. The exported summary contains measurements and source identifiers only.", "",
        "One DistilCamemBERT source-offset mismatch interrupted the first quality pass: OCR contains an n followed by U+0303 COMBINING TILDE, normalized to a composed character whose original offset omitted the combining mark. The evaluation adapter now extends that offset only when Unicode composition and the tokenizer normalizer agree, with an adjacent source-token anchor. The failed deployment was rerun fully; the other three completed deployments had no uncovered characters and never enter the repaired branch. All 3,108 inputs were audited for the three token classifiers, with zero remaining incomplete inputs. The affected mark is outside reference entities. Input text, gold boundaries, weights and thresholds were unchanged. A missing ordinary character still causes failure. The run manifest retains both the original and resumed implementation hashes.", "",
        "Reproduce from the repository root with the isolated evaluation Python:", "",
        "```powershell", "evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.additional_cohort",
        "evaluation/ner/.venv/Scripts/python.exe -m unittest evaluation.ner.test_additional_reference -v",
        "evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.run_additional",
        "evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.additional_analysis",
        "evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.additional_report", "```", ""]
    (BASE / "report-additional-20261006.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote report-additional-20261006.md")


if __name__ == "__main__":
    main()
