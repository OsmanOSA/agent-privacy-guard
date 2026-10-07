# French NER evaluation

Compare detection quality and local execution cost on published French texts with existing reference annotations. Active model candidates declare permissive licenses allowing commercial use. Dataset eligibility is checked separately before fetching, preparing or scoring. This study uses no newly generated documents or invented personal values.

## Corpora

| Corpus | Reference annotations | Evaluation role | Data license |
| --- | --- | --- | --- |
| [WikiNER-fr-gold](https://huggingface.co/datasets/danrun/WikiNER-fr-gold) | Manually revised French Wikipedia NER annotations | Main person recognition benchmark | CC BY 4.0 |
| [FENEC v1 selected documents](https://github.com/alicemillour/FENEC) | Published BRAT reference spans | Six-document source comparison, excluding WikiNER | CC BY 2.5; CC BY-SA 2.0 and 4.0 by source |
| [HIPE 2022 hipe2020 French](https://github.com/hipe-eval/HIPE-2022-data) | Annotated historical newspaper articles with OCR noise | Excluded from this product-oriented evaluation | CC BY NC SA 4.0 |

WikiNER-fr-gold has 26,754 source sentences. Its published `train` designation is a storage convention; the authors prescribe no train/dev/test split. Grouping by the SHA-256 of the input text assigns 2,640 sentences to calibration and 24,114 to test. This is our evaluation split, not an official benchmark split. See the [corpus paper](https://arxiv.org/abs/2411.00030).

HIPE was initially downloaded with 43 French dev and 43 test articles. Its non-commercial clause does not authorize this product-oriented evaluation. It is now disabled in `sources.json`; fetch and preparation skip it, and scoring rejects it. Existing ignored local files are retained as an inactive archive. See the [source description](https://github.com/hipe-eval/HIPE-2022-data/blob/main/documentation/README-hipe2020.md) and [license terms](https://creativecommons.org/licenses/by-nc-sa/4.0/).

These are real source texts; their entity inventories can include historical people, fictional characters or collective names. They test recognition according to the corpus annotation scheme. WikiNER does not provide comprehensive ground truth for private postal addresses, email addresses or all PII. A location label must not be presented as a postal-address label. A separate published PII corpus with verified provenance is needed before making broader privacy claims.

## Files

- `sources.json`: source URLs, pinned revisions, byte counts and SHA-256 hashes.
- `candidates.json`: model shortlist and outstanding artifact checks.
- `licensing.md`: commercial-use policy and redistribution obligations.
- `license-evidence.json`: pinned model declarations, notice hashes and installed runtime inventory.
- `license_policy.py`: eligibility filters applied by the evaluation tools.
- `protocol.md`: common inputs, metrics, timing and decision rules.
- `fetch.py`: reproducible download and integrity checks using the standard library.
- `readers.py` and `tagged_text.py`: source annotation readers and offset conversion.
- `prepare.py`: normalized inputs, annotations, split counts and integrity audit.
- `metrics.py` and `score.py`: common scoring independent of the model runtime.
- `window_batch.py` and `tools/check_window_batches.py`: bounded CPU window-batch experiment, reference-span regression checks, counterbalanced timing and isolated worker memory. Results are in `window-batches-20261006.json`; batch one is retained.
- `data/raw/`: original downloaded files, source documentation and HIPE license.
- `data/prepared/`: JSONL input text and reference character spans.
- `results/`: audits, future predictions and measurements.

Data, weights and generated results are ignored by Git. Dataset and model licenses remain separate from the repository MIT license. The project license does not replace upstream licenses.

## Model shortlist

| Candidate | Declared weight license | Role in the comparison |
| --- | --- | --- |
| [GLiNER2 PII](https://huggingface.co/fastino/gliner2-privacy-filter-PII-multi) | Apache 2.0 | Existing person-only implementation baseline |
| [Masker Mini](https://huggingface.co/divergentlabs/masker-mini) | Apache 2.0 | Small multilingual PII encoder |
| [Nym multilingual small](https://huggingface.co/Wismut/nym-pii-multilingual-small) | MIT | Compact multilingual PII comparator |
| [DistilCamemBERT NER](https://huggingface.co/cmarkea/distilcamembert-base-ner) | MIT | French distilled NER comparator |
| [GLiNER multilingual PII v1](https://huggingface.co/urchade/gliner_multi_pii-v1) | Apache 2.0 | Larger multilingual PII quality reference |

Both DistilCamemBERT NER and Masker Mini disclose WikiNER training exposure; Masker explicitly credits WikiNER-fr-gold. Their WikiNER scores cannot establish unseen-data generalization. The selected FENEC documents provide different source material and annotations, with possible pretraining overlap still unresolved. Versions, artifact hashes and license declarations are recorded in `candidates.json`.

Rampart and spaCy are recorded as excluded candidates in `candidates.json`. Rampart's CC BY 4.0 permits commercial use with attribution; its exclusion follows our narrower preference for software licenses. The LGPL-LR license of the spaCy French weights is also outside that preference. Neither exclusion means all non-MIT licenses prohibit commercial use.

## Prepare the data

Run from the repository root with Python 3.10 or newer:

```powershell
python -m evaluation.ner.fetch
python -m evaluation.ner.prepare
```

Preparation validates file hashes and span bounds, detects duplicate inputs and rejects text shared across calibration and test. The current audit reports no duplicate inputs or cross-split leakage. Source documents remain available in their original format.

WikiNER publishes tokens rather than original whitespace. Prepared text joins those tokens with single spaces. Offsets refer to these explicit prepared texts. No HIPE inputs enter active preparation or scoring.

## Score model predictions

Each prediction JSONL record contains `id`, `text_sha256`, `spans` and optionally `elapsed_ms`. Each span contains `kind`, `start`, `end`, using Python Unicode character offsets and an exclusive end. The common person label is `PERSON`. Offsets must refer to the complete prepared input, even when an adapter processes overlapping windows.

```powershell
python -m evaluation.ner.score --corpus evaluation/ner/data/prepared/wikiner-fr-gold.jsonl --predictions evaluation/ner/results/MODEL.predictions.jsonl --split test --kind PERSON --output evaluation/ner/results/MODEL.quality.json
```

The scorer refuses missing records, duplicate IDs, invalid offsets and predictions made on a different input. Exact precision, recall and F1 accompany complete mention coverage and non-whitespace character coverage. Scores aggregate counts across records. An undefined rate is `null`.

## Run the model comparison

The initial study freezes 512 calibration sentences, 2,000 WikiNER test sentences and 300 shared timing inputs. Each model has three timing passes, in isolated sequential CPU processes. It also scores six complete FENEC documents without changing the calibrated thresholds. This is an initial sample study, not an evaluation of all 26,754 WikiNER sentences or the full FENEC corpus. The earlier synthetic probes are excluded.

Use Python 3.12 and a separate research environment. PyTorch and the model downloads can use several gigabytes. The existing Privacy Guard model and hook are not reinstalled by these commands.

```powershell
py -3.12 -m venv evaluation/ner/.venv
$py = 'evaluation/ner/.venv/Scripts/python.exe'
& $py -m pip install torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu
& $py -m pip install -r evaluation/ner/requirements.txt
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
& $py -m evaluation.ner.fetch
& $py -m evaluation.ner.prepare
& $py -m evaluation.ner.cohort
& $py -m evaluation.ner.fenec
& $py -m evaluation.ner.fetch_models
& $py -m evaluation.ner.check_distil_artifact
& $py -m evaluation.ner.run_comparison
& $py -m evaluation.ner.aggregate
& $py -m evaluation.ner.write_report
```

The baseline requires the already installed person-only GLiNER2 export with the hash in `candidates.json`. Its exporter is [tools/build_name_model.py](../../tools/build_name_model.py); matching the pinned local artifact is required to reproduce this particular baseline. The other model weights are fetched from pinned upstream revisions. The larger GLiNER tokenizer and encoder configuration use the pinned Microsoft revision recorded by `fetch_models.py` and `run.json`. Prediction text hashes, complete record coverage and repeat timing prediction hashes are checked before aggregation.

`summary-20261005.json` contains the numerical results and paired bootstrap intervals. Raw inputs, predictions, weights, measurements and resource receipts remain under ignored directories. `distil-artifact-check.json` records the failed quantized graph check on real calibration records. Its FP32 alternative participates in the five-model comparison. These are deployment-variant comparisons: precision, runtime and tokenizer behavior are recorded, and are not held identical across architectures.

The [completed initial comparison](report-20261005.md) reports all five models, the FENEC source control and the limits of the current evidence. It supports a next-candidate recommendation, not a production replacement.

The short adapters, decoder, worker, runner and aggregator are separate modules. Run them from the repository root with `python -m evaluation.ner.MODULE`.

## Additional French references

The [source selection](additional-datasets.md) identifies three active local evaluation corpora and one reserve. Deep Sequoia outside Wikipedia and Europeana French OCR have human PERSON references. SoDUCo provides human nested references for addresses and names, but its PER label combines people and businesses. Its score is reported as a separate name-or-business diagnostic for the existing person-only deployments. AjMC remains on hold because of contradictory license notices.

`additional_cohort.py` prepares these sources from the pinned `data/raw/additional-20261006/` assets, freezes the quality and timing inputs, and records exclusions. The general `prepare.py` delegates these datasets to that workflow. `test_additional_reference.py` checks alignment and scoring against the published files. The five deployments retain their earlier thresholds; no new calibration or training is performed.

```powershell
evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.fetch
evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.additional_cohort
evaluation/ner/.venv/Scripts/python.exe -m unittest evaluation.ner.test_additional_reference -v
evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.run_additional
evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.additional_analysis
evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.additional_report
```

`additional-window-audit.json` checks complete legacy-window coverage and the word limit. `additional-overlap-audit.json` records comparison with the available WikiNER and FENEC text. Content-free results are written to `summary-additional-20261006.json` and `report-additional-20261006.md`; raw predictions and reference surfaces remain local and ignored.

## Additional MIT deployments

`mit-candidates.json` pins spaCy multilingual 3.8.0, hmBERT Tiny French NER and CATIE ModernCamemBERT. `fetch_mit.py` fetches their original artifacts and records hashes in `mit-artifacts.json`. Extra runtime dependencies are limited to the isolated evaluation environment; `requirements-mit.txt` records the direct versions. Existing package versions are preserved by the captured local pip constraints.

`run_mit.py` reuses the same three frozen reference corpora, calibrates each new candidate on the original WikiNER calibration partition, and measures three timing passes. DistilCamemBERT quality predictions are retained and rescored, while its latency is measured again as a contemporaneous control. hmBERT's Europeana result is explicitly exposed to training and cannot demonstrate independent generalization. SoDUCo remains a separate name-or-business diagnostic.

The validated numerical results and final single-model selection are recorded in `summary-mit-20261006.json`, `mit-selection.json` and [the final MIT comparison](report-mit-20261006.md). These measurements concern local CPU deployments; they do not change the production hook or install a replacement model.

## Selected-model long-input latency

The [length probe](report-latency-length-20261006.md) measures contiguous published Europeana OCR excerpts at approximately 500, 1,000, 2,000 and 4,000 detector tokens. `latency-length-20261006.json` preserves all five warm timings per length and artifact fingerprints without source text. Run `evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.latency_length` from the repository root. This is a latency-only probe of the selected ONNX FP32 deployment, not a new quality comparison or a production integration. The 4,000-token input takes about 2.45 seconds in this run; the earlier short-input latencies must not be generalized to complete documents.

`latency_cache.py` reconstructs the exact same 3,997-token excerpt and measures the bounded service cache with the selected detector. `latency-cache-20261006.json` preserves uncached/miss timings, five hits and exact finding equality without source text. Run `evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.latency_cache`. These timings concern only `find_names`; they exclude the full hook and do not install DistilCamemBERT into the production service.

## Runtime integration

The selected detector was integrated and deployed locally after the comparison. `distil-runtime-validation-20261006.json` records exact agreement with frozen predictions on 36 real corpus inputs and the long excerpt. `distil-installed-check-20261006.json` records the installed native hook's restoration/reprotection cycle and full local hook timings. `distil-deployment-20261006.json` records artifact pins, preserved user state and validation. These later receipts do not alter the comparison scores or imply observation of a Claude network request.
