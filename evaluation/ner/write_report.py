"""Write a content-free research report from the verified numerical summary."""

import json
import statistics

from .fetch import BASE

NAMES = {"gliner2-privacy-filter-PII-multi": "GLiNER2 current export", "masker-mini": "Masker Mini",
         "nym-pii-multilingual-small": "Nym small", "distilcamembert-base-ner": "DistilCamemBERT FP32",
         "gliner_multi_pii-v1": "GLiNER multilingual v1"}


def percent(value):
    return f"{100 * value:.2f}" if value is not None else "undefined"


def interval(bounds):
    return "–".join(percent(value) for value in bounds)


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |",
            *["| " + " | ".join(map(str, row)) + " |" for row in rows], ""]


def main():
    study = json.loads((BASE / "summary-20261005.json").read_text(encoding="utf-8"))
    models = study["models"]
    fastest = models["masker-mini"]
    baseline = models["gliner2-privacy-filter-PII-multi"]
    machine = study["run"]["machine"]
    lines = ["# French person detection evaluation", "",
        "Five candidate deployments were evaluated on existing French reference annotations. Masker Mini is the strongest candidate for a smaller and faster deployment in this initial comparison. The evidence does not justify calling it a reliable privacy filter or replacing the production detector yet.", "",
        f"Its median warm latency is {fastest['latency_ms']['p50']:.2f} ms versus {baseline['latency_ms']['p50']:.2f} ms for the current GLiNER2 export ({baseline['latency_ms']['p50'] / fastest['latency_ms']['p50']:.1f} times faster on these inputs). Its weights occupy {fastest['weights_bytes'] / 1e6:.1f} MB. However, only 44 of 57 individually named person mentions are completely covered on the selected FENEC documents. No model completely covers more than 45 of those 57 mentions.", "",
        "## Study conditions", "",
        f"The controlled run started at {study['run']['started_at']} and finished at {study['run']['finished_at']}. CPU: {machine['CPU']['Name'].strip()}, {machine['CPU']['NumberOfCores']} physical cores, {machine['CPU']['NumberOfLogicalProcessors']} logical processors; RAM: {machine['RAMBytes'] / 2**30:.2f} GiB. Windows 11, Python {study['run']['versions']['python']}; batch size one and four intra-operation threads. CPU only.", "",
        "The frozen WikiNER sample contains 512 calibration sentences and 2,000 test sentences, with 1,216 reference person mentions and 1,182 sentences without a person mention. This split belongs to this harness, not the corpus authors. The sample was selected before model inference by a recorded hash seed. All five models completed every input. Thresholds were chosen only on calibration by exact F1 from the same five-value grid.", "",
        "The FENEC control contains six complete documents, 30,579 characters and 72 person mentions: 57 individual and 15 collective names. It excludes the WikiNER document and uses the other six v1 sources declaring CC BY or CC BY-SA. Thresholds transfer from WikiNER calibration without further tuning. The inputs and gold annotations were published by their authors; no documents or personal values were invented for this study.", "",
        "## WikiNER sample results", "",
        "Exact F1 requires the predicted category and both boundaries to match. Complete coverage requires all non-whitespace characters of the reference mention to be covered, including punctuation. Rates below are percentages. Confidence intervals use 1,000 paired sentence bootstrap resamples; they describe sample uncertainty, not unseen-data generalization.", ""]
    lines += table(["Model", "Threshold", "Precision", "Recall", "F1 [95% CI]", "Complete coverage / 1216", "Negative sentence FP / 1182"], [
        [NAMES[name], model["threshold"], percent(model["wikiner"]["exact_precision"]), percent(model["wikiner"]["exact_recall"]),
         f"{percent(model['wikiner']['exact_f1'])} [{interval(model['confidence_95']['wikiner']['exact_f1'])}]",
         f"{model['wikiner']['fully_covered_entities']} ({percent(model['wikiner']['full_entity_coverage'])}%)",
         f"{model['wikiner']['negative_records_with_predictions']} ({percent(model['wikiner']['negative_record_false_positive_rate'])}%)"]
        for name, model in models.items()])
    lines += ["Both Masker Mini and DistilCamemBERT disclose WikiNER training exposure. Masker specifically credits WikiNER-fr-gold among its training/distillation sources. A split made locally cannot undo that exposure. Other models may also have seen Wikipedia text during pretraining. These scores measure behavior on this reference sample and must not be presented as an unbiased unseen-data leaderboard.", "",
        "## FENEC source comparison", "",
        "FENEC uses Quæro annotations with different boundary and collective-name conventions. All `pers.*` labels map to PERSON. Role labels `func.*` are excluded. The table reports both the complete 72-mention inventory and coverage of the 57 individual mentions. All six documents contain person mentions, so a negative-document false-positive rate is undefined.", ""]
    lines += table(["Model", "Exact F1 [95% CI]", "Complete / 72", "Individual names complete / 57", "Individual partially covered", "Individual wholly missed"], [
        [NAMES[name], f"{percent(m['fenec']['exact_f1'])} [{interval(m['confidence_95']['fenec']['exact_f1'])}]",
         f"{m['fenec']['fully_covered_entities']} ({percent(m['fenec']['full_entity_coverage'])}%)",
         f"{m['fenec_individual_person_only']['fully_covered_entities']} ({percent(m['fenec_individual_person_only']['full_entity_coverage'])}%)",
         m["coverage_errors"]["fenec"]["pers.ind"].get("partial", 0), m["coverage_errors"]["fenec"]["pers.ind"].get("missed_entirely", 0)]
        for name, m in models.items()])
    lines += ["Six document clusters provide limited statistical information. The small differences in individual coverage do not establish a winner. FENEC's separate source annotations also do not prove absence from every model's pretraining. Different source genres and annotation policies contribute to the lower scores; they must not be interpreted as a measured rate of private-data leakage in the product.", "",
        "## Local execution cost", "",
        "Three passes process the same 300 texts in a recorded shuffled order, rotating model order between passes: 900 observations per model, 4,500 overall. Five calibration texts warm each process. Latency includes tokenization, inference, decoding and windows. Corpus loading and scoring are excluded. All repeat predictions match the corresponding quality predictions. Weights are cached on disk; completed predictions are not reused.", ""]
    lines += table(["Model", "Weights MB", "Peak process MiB", "Median ms", "p95 ms", "Mean ms", "Median loader ms"], [
        [NAMES[name], f"{m['weights_bytes']/1e6:.1f}", f"{m['peak_process_memory_bytes']/2**20:.1f}",
         f"{m['latency_ms']['p50']:.2f}", f"{m['latency_ms']['p95']:.2f}", f"{m['latency_ms']['mean']:.2f}",
         f"{statistics.median(m['model_load_ms_by_pass']):.0f}"] for name, m in models.items()])
    lines += ["Peak memory is Windows process peak working set, including framework and initialization allocations. It is not steady-state detector memory. Loader timing starts after harness imports and may include lazy adapter framework imports; it is not full process-startup timing. Power-scheme querying failed and is recorded as unavailable. Background OS load, thermal state and CPU frequency were not controlled.", "",
        "The timing sample contains 145 texts shorter than 128 characters, 154 between 128 and 511, and one longer text. That one text has only three observations; long-document p95 cannot be inferred from it. The six FENEC document measurements are retained as exploratory single-pass observations, not included in the controlled short-text timing table.", "",
        "## Deployment variants and artifact checks", ""]
    lines += table(["Model", "Measured implementation", "Declared weight license"], [
        [NAMES[name], m["backend"], "MIT" if name in {"nym-pii-multilingual-small", "distilcamembert-base-ner"} else "Apache 2.0"] for name, m in models.items()])
    lines += ["Nym's int8-folder export stores quantized embeddings and fp16 body weights while computing in FP32. It is not a full INT8 execution backend. GLiNER v1 is the original FP32 PyTorch checkpoint with strict state-dict loading; the other models use ONNX Runtime. The current GLiNER2 baseline is a person-only INT4 export, not the complete upstream PII model. Its native word-token cache remains enabled. Comparisons concern these deployable variants, not architecture speed under identical precision.", "",
        "DistilCamemBERT's published quantized graph failed a calibration-only equivalence check: at threshold 0.5 it found none of 19 reference person mentions in 32 real calibration sentences, while the FP32 graph found 18 exactly. Native slow and fast tokenizers returned matching IDs on 20 calibration inputs. The root cause of the graph failure is unresolved; only the FP32 graph participates in the reported comparison. The diagnostic and exact artifact hashes are retained in `distil-artifact-check.json`.", "",
        "Complete source-window coverage was audited on all 2,518 calibration, quality and FENEC inputs. Legacy GLiNER windows never exceed 169 words against its 384-word limit. Token classifiers reject inputs whose overlapping token offsets omit a non-whitespace source character. The GLiNER tokenizer emits upstream byte-fallback and regex warnings; its native loading behavior was retained, and repeated predictions remained identical on the 300 common timing inputs.", "",
        "## Interpretation and next decision", "",
        "Keep Masker Mini as the leading candidate for a subsequent privacy-focused validation: it reduces weight size and measured warm latency substantially while retaining strong WikiNER person coverage. DistilCamemBERT has better exact precision on WikiNER but lower complete mention coverage and larger weights. Nym's tested compressed deployment has lower person coverage in both samples. Neither GLiNER deployment provides enough improvement on these inputs to offset its measured cost, but FENEC's small coverage differences remain inconclusive.", "",
        "No production detector has been replaced. These results do not assess full PII recall: private addresses, emails, phone numbers, identifiers and secrets need their own published reference annotations. No acceptable omission rate or end-to-end workflow latency budget has been agreed. Set those requirements before selecting a deployment; then validate names and the required additional categories on a larger eligible source corpus and measure the complete hook workflow. Recalibration or model combinations must be separate evaluated systems, never promises inferred from these scores.", "",
        "## Evidence and reproduction", "",
        "See [README](README.md) for isolated environment setup and commands, [protocol](protocol.md) for mappings and timing, [license policy](licensing.md) for commercial-use conditions, [numerical summary](summary-20261005.json) for per-source scores, intervals, length bands, CPU time, hashes and repeated observations, and [artifact diagnostic](distil-artifact-check.json). Ignored local results retain the source-aligned predictions. The project MIT license does not replace model or dataset terms.", "",
        "Sources: [WikiNER-fr-gold](https://huggingface.co/datasets/danrun/WikiNER-fr-gold), [FENEC pinned source table](https://github.com/alicemillour/FENEC/tree/3a975635d57712096d8ebf859d842042c782837b), [Millour et al. 2022](https://aclanthology.org/2022.jeptalnrecital-taln.8/), [Masker pinned model card](https://huggingface.co/divergentlabs/masker-mini/blob/beb7235d454aa4488b6ee1cd47f417caa12a6d15/README.md), [DistilCamemBERT pinned card](https://huggingface.co/cmarkea/distilcamembert-base-ner/blob/e539d952f70088b450c300c28ba455da87f2dc4b/README.md).", ""]
    (BASE / "report-20261005.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote evaluation/ner/report-20261005.md")


if __name__ == "__main__":
    main()
