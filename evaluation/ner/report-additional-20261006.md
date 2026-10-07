# Additional French reference evaluation

DistilCamemBERT FP32 has the highest exact PERSON F1 on the retained non-Wikipedia Sequoia sentences in this run. The corpus-specific tables below compare the same five deployments against published human reference annotations. These are transferred-threshold measurements, with no new fine-tuning or calibration.

Sequoia and Europeana evaluate PERSON with different reference conventions. SoDUCo evaluates coverage of its broader name-or-business references by the same person-only outputs. Its diagnostic score is not a person-only leaderboard. No address inference score is reported.

## Inputs and reference annotations

| Corpus | Inputs | Reference target | Gold mentions | Negative inputs |
| --- | --- | --- | --- | --- |
| Deep Sequoia outside Wikipedia | 2084 | PERSON | 270 | 1856 |
| Europeana French OCR | 512 | PERSON | 1333 | 159 |
| SoDUCo name-or-business diagnostic | 512 | NAME_OR_BUSINESS | 512 | 0 |

All eligible non-Wikipedia Sequoia sentences were retained after documented exclusions and exact deduplication. Europeana and SoDUCo each use 512 records selected by a SHA-256 seed before inference. Each corpus has 75 common timing inputs and three shuffled timing passes, giving 225 timed observations per deployment per corpus.

A reference is a text plus the expected category and character boundaries for every annotated occurrence. Exact precision, recall and F1 require matching both boundaries and category. Full coverage requires all non-whitespace characters of a reference mention, including punctuation, to be covered. Pooled scores below are micro scores; no incompatible corpus scores are pooled together.

## Deep Sequoia outside Wikipedia

| Deployment | Threshold | Precision % | Recall % | F1 % [95% interval] | Fully covered / gold | Partial | Entirely missed | Negative FP % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GLiNER2 current INT4 export | 0.6 | 14.20 | 60.00 | 22.96 [19.52–26.53] | 225/270 | 0 | 45 | 34.59 |
| Masker Mini INT4 | 0.25 | 49.75 | 74.44 | 59.64 [54.52–64.39] | 245/270 | 0 | 25 | 6.90 |
| Nym small compressed export | 0.4 | 63.32 | 60.74 | 62.00 [55.27–68.31] | 205/270 | 11 | 54 | 1.56 |
| DistilCamemBERT FP32 | 0.5 | 66.45 | 75.56 | 70.71 [65.30–75.90] | 235/270 | 5 | 30 | 2.69 |
| GLiNER multilingual v1 FP32 | 0.6 | 18.89 | 54.44 | 28.05 [23.36–32.73] | 217/270 | 0 | 53 | 25.22 |

| Deployment | Warm median ms | Warm p95 ms | Observations |
| --- | --- | --- | --- |
| GLiNER2 current INT4 export | 60.64 | 140.29 | 225 |
| Masker Mini INT4 | 5.29 | 10.93 | 225 |
| Nym small compressed export | 10.92 | 22.94 | 225 |
| DistilCamemBERT FP32 | 9.95 | 23.62 | 225 |
| GLiNER multilingual v1 FP32 | 154.80 | 223.62 | 225 |

## Europeana French OCR

| Deployment | Threshold | Precision % | Recall % | F1 % [95% interval] | Fully covered / gold | Partial | Entirely missed | Negative FP % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GLiNER2 current INT4 export | 0.6 | 45.66 | 52.44 | 48.81 [43.29–54.19] | 1096/1333 | 15 | 222 | 54.09 |
| Masker Mini INT4 | 0.25 | 49.90 | 54.09 | 51.91 [47.71–55.82] | 1009/1333 | 65 | 259 | 31.45 |
| Nym small compressed export | 0.4 | 44.10 | 37.88 | 40.76 [36.64–45.00] | 888/1333 | 52 | 393 | 13.84 |
| DistilCamemBERT FP32 | 0.5 | 61.11 | 68.72 | 64.69 [60.99–68.20] | 1153/1333 | 43 | 137 | 20.75 |
| GLiNER multilingual v1 FP32 | 0.6 | 38.85 | 39.08 | 38.97 [34.03–44.05] | 1022/1333 | 11 | 300 | 61.01 |

| Deployment | Warm median ms | Warm p95 ms | Observations |
| --- | --- | --- | --- |
| GLiNER2 current INT4 export | 367.36 | 433.52 | 225 |
| Masker Mini INT4 | 24.47 | 31.10 | 225 |
| Nym small compressed export | 60.24 | 76.55 | 225 |
| DistilCamemBERT FP32 | 64.25 | 82.63 | 225 |
| GLiNER multilingual v1 FP32 | 446.67 | 616.48 | 225 |

## SoDUCo name-or-business diagnostic

| Deployment | Threshold | Precision % | Recall % | F1 % [95% interval] | Fully covered / gold | Partial | Entirely missed | Negative FP % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GLiNER2 current INT4 export | 0.6 | 35.85 | 54.69 | 43.31 [38.07–48.27] | 282/512 | 139 | 91 | undefined |
| Masker Mini INT4 | 0.25 | 22.05 | 25.59 | 23.69 [19.43–27.56] | 135/512 | 133 | 244 | undefined |
| Nym small compressed export | 0.4 | 22.73 | 20.51 | 21.56 [17.47–25.72] | 229/512 | 100 | 183 | undefined |
| DistilCamemBERT FP32 | 0.5 | 37.38 | 46.88 | 41.59 [36.49–46.68] | 241/512 | 187 | 84 | undefined |
| GLiNER multilingual v1 FP32 | 0.6 | 82.02 | 77.54 | 79.72 [76.34–83.16] | 440/512 | 24 | 48 | undefined |

| Deployment | Warm median ms | Warm p95 ms | Observations |
| --- | --- | --- | --- |
| GLiNER2 current INT4 export | 47.81 | 68.13 | 225 |
| Masker Mini INT4 | 3.78 | 5.47 | 225 |
| Nym small compressed export | 9.34 | 15.05 | 225 |
| DistilCamemBERT FP32 | 8.34 | 13.08 | 225 |
| GLiNER multilingual v1 FP32 | 142.00 | 174.59 | 225 |

## Reference and interpretation limits

[Deep Sequoia 9.2](https://deep-sequoia.inria.fr/) uses the typed PARSEME-FR NE layer in column 11, aligned with original sentence text. Noun supersenses are ignored. All 996 Wikipedia sentences are excluded; one sentence with a discontinuous PERSON annotation is excluded as a whole because this task requires continuous spans. Eighteen repeated source sentences are deduplicated. The retained set contains 270 PERSON references, with separate source-domain counts and scores in the JSON summary. Its medical sections are negative-heavy.

[Europeana Newspapers](https://github.com/EuropeanaNewspapers/ner-corpora) supplies human labels in an IO export. Its 205,916 source token rows include two literal hash-sign tokens, not metadata comments. The reader partitions contiguous source tokens into chunks of at least 128 tokens, ending outside entities, and joins tokens with spaces. Original newspaper whitespace and article boundaries are unavailable in this export. Exact F1 therefore uses IO-derived contiguous spans; adjacent same-category entities cannot be separated reliably. The authors also warn about OCR and removed noisy sentence fragments. Treat this result as an OCR stress test.

[SoDUCo v2](https://zenodo.org/records/8167628) has aligned text and human nested XML references. Three inconsistent text/XML records and eight repeated texts are excluded before sampling. The [authors' label definition](https://arxiv.org/html/2302.10204) combines people and businesses in PER. Person-only predictions are relabeled NAME_OR_BUSINESS for this diagnostic comparison; this does not change their detected spans or make them business detectors. The full prepared references preserve ADDRESS, STREET and STREET_NUMBER. Those categories await compatible inference outputs before scoring. The selected entries all contain a name-or-business reference, so negative-input false-positive rate is undefined.

AjMC is held aside. No invented text, generated names or model-created reference annotations enter these cohorts. Different sources remove dependence on the WikiNER evaluation partition, but undisclosed training or pretraining exposure remains possible.

Intervals use 1,000 paired bootstrap resamples: Sequoia sentences, Europeana source-token blocks and SoDUCo source pages. Sequoia sentence intervals do not account for article-level dependence because original article groups are not reconstructed. Europeana blocks approximate local dependence rather than known documents. Intervals describe sample uncertainty, not absence of training exposure or annotation errors.

## Execution and reproducibility

Run: 2026-10-05T22:58:14.059909+00:00 to 2026-10-05T23:29:05.801210+00:00. CPU only, batch size one, four intra-operation threads, isolated sequential processes. Model artifacts and the decoding rules are unchanged from the initial comparison. Timing includes tokenization, all inference windows and decoding, after warm-up; excludes scoring, model loading and the full hook workflow. Model order rotates between passes. Background workload and power state are not controlled.

Every saved quality score was recomputed from its predictions and reference inputs. All timing IDs and prediction hashes match the corresponding quality run. Parser tests verify source alignment, preservation of nested references and source tokens, an identity-reference F1 of 1, and rejection of shifted boundaries as exact matches. Raw text, reference surfaces, weights and predictions stay in ignored local folders. The exported summary contains measurements and source identifiers only.

One DistilCamemBERT source-offset mismatch interrupted the first quality pass: OCR contains an n followed by U+0303 COMBINING TILDE, normalized to a composed character whose original offset omitted the combining mark. The evaluation adapter now extends that offset only when Unicode composition and the tokenizer normalizer agree, with an adjacent source-token anchor. The failed deployment was rerun fully; the other three completed deployments had no uncovered characters and never enter the repaired branch. All 3,108 inputs were audited for the three token classifiers, with zero remaining incomplete inputs. The affected mark is outside reference entities. Input text, gold boundaries, weights and thresholds were unchanged. A missing ordinary character still causes failure. The run manifest retains both the original and resumed implementation hashes.

Reproduce from the repository root with the isolated evaluation Python:

```powershell
evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.additional_cohort
evaluation/ner/.venv/Scripts/python.exe -m unittest evaluation.ner.test_additional_reference -v
evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.run_additional
evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.additional_analysis
evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.additional_report
```
