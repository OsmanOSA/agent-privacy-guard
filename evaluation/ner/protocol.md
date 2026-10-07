# French model comparison protocol

The first comparison measures person recognition on published French gold corpora permitted for commercial-purpose evaluation. WikiNER-fr-gold and six selected FENEC v1 documents are active; HIPE is excluded because of its non-commercial condition. Exact entity F1 describes boundary and classification quality; complete mention coverage describes whether the predicted spans cover an entire reference mention. Report both because partial detection can leave identifying characters visible.

## Common evaluation conditions

Apply the [license policy](licensing.md) before model execution. Active candidates declare MIT, Apache 2.0 or an accepted permissive software license. Keep the license decision separate from measured accuracy. Record base-model and tokenizer origins and retain upstream notices when distributing artifacts.

Freeze corpus hashes, artifact revisions, decoder behavior and label mappings before evaluating the test splits. Use calibration data to select thresholds and window settings. Report a common reference threshold of 0.5 as well as the calibrated setting; 0.5 is not described as each author's native default. Give every model the same calibration opportunity. Do not tune from test errors. Wikipedia-derived inputs can overlap pretraining or model training; document disclosed training sources. A held-out split in this harness does not establish that a model has never seen the source text.

All models receive the same prepared text without changing its values, adding names or rewriting paragraphs. Retain every record, including those with no person annotation. The initial task maps person name labels to `PERSON`. Given-name and surname outputs require a declared, fixed merging rule; join adjacent person fragments only across whitespace. Do not merge across an intervening ordinary word to improve scores.

Compare model outputs alone first. The installed GLiNER2 export supports person names only, so it must be named as that specific export rather than the complete multilingual PII model. It can serve as the current implementation baseline. General French NER and broader PII models participate in the same person task. A later comparison can add the same deterministic rules to each candidate; keep its results separate.

Process complete inputs. For token limits, use overlapping windows and map offsets to the original prepared record. Merge duplicate predictions deterministically. Never silently truncate a document or omit a failed inference. Record failures and mark any incomplete run as ineligible for ranking.

## Quality measurements

Report results separately for each corpus and each category with its denominator:

- Exact span and category precision, recall and micro F1.
- Complete mention coverage: all non-whitespace characters in a reference span covered by predictions of the same category. Count every occurrence by its offsets.
- Non-whitespace character precision and recall. Punctuation inside a reference mention counts.
- False-positive rate on records with no reference person mention.
- Breakdown by input length and number of reference mentions; preserve OCR and source annotation caveats.

When another eligible corpus is added, report it separately rather than producing a headline score dominated by Wikipedia. Keep source annotation policies visible: NER person labels do not necessarily mean private information. Add document-level paired bootstrap confidence intervals before interpreting small differences as a ranking. These intervals estimate sample uncertainty, not annotation reliability or domain coverage. A candidate with disclosed WikiNER training needs an independent corpus before its score supports a generalization-based selection.

## Execution cost

Use the same CPU, inference provider and thread limit for every comparable run. Execute models sequentially in isolated processes with batch size one. Record CPU model, OS, Python and library versions, power settings and model file sizes. Keep unrelated workload stable. Run at least three passes with a recorded shuffled order; rotate model order between passes.

Separate process startup and model initialization from warm execution. Warm the model before timing. Warm latency includes tokenization, inference, decoding and all long-input windows; excludes corpus loading and scoring. Cache model weights, never prediction results. Report p50 and p95 per input-length band, aggregate latency, throughput, process CPU time and peak process memory. A three-pass repeated study requires raw observations and a run manifest; the generic scorer's optional one-observation-per-record latency summary is not sufficient by itself.

The model timing study does not measure hook startup, transport or file restoration. Once a candidate is selected, measure those costs through the complete Privacy Guard workflow in a separate integration run.

## Model choice

Present quality first, followed by latency, memory, weight size, runtime and license. Identify the candidates for which another model is neither more accurate nor cheaper across the measured criteria. Choose a protection-quality requirement and workflow latency budget before the final selection. No acceptable leakage rate or millisecond target has been fixed yet; preserve the measured tradeoffs instead of inventing one.

Only consider combining models after their independent error analyses show complementary misses. Measure any combination as a new system with its own quality and execution cost. Do not infer its performance by adding published scores or unrelated timings.

## Frozen initial study

The cohort was fixed before the five-model comparison: 512 calibration records and 2,000 test records sampled by a declared SHA-256 seed, then 300 common timing records from the test sample. `cohort.json` retains IDs through the frozen JSONL hashes. Calibration selects among 0.15, 0.25, 0.4, 0.5 and 0.6 by exact F1, complete coverage, precision, then the higher threshold. The selected threshold is transferred to FENEC without retuning.

The FENEC subset consists of Wikinews, L'Est Républicain, UD French GSD and three Rhapsodie transcripts: all six non-WikiNER v1 documents declaring CC BY or CC BY-SA in the repository source table. Source text is preserved byte-for-byte after UTF-8 decoding; BRAT person surface values must agree with Unicode character offsets. All `pers.*` labels map to PERSON, including collective names; `func.*` roles are excluded. Individual-person coverage is also reported separately. This is a selected subset with different annotation conventions, not the original paper's complete benchmark.

Token classifiers use native token IDs and overlapping 512-token windows with a 64-token overlap. The current GLiNER2 export retains its 200-word windows with 40-word overlap and native word-token cache. GLiNER v1 uses 700-character windows with a 150-character overlap and the single label `person`. All predicted fragments merge across overlap or whitespace only. Common inference timing includes these implementations' own tokenization behavior; it does not cache completed predictions.

Exact F1 and complete mention coverage receive 1,000 paired bootstrap resamples, using a WikiNER sentence or a FENEC document as the resampling unit. FENEC intervals have only six document clusters and should not settle small ranking differences. Latency uses nearest-rank p95, batch size one, three shuffled passes over the same 300 texts, rotated model order and four intra-operation threads. The baseline ONNX session uses default sequential inter-operation execution; token classifiers and PyTorch explicitly use one inter-operation thread. Only one distinct timing sentence has at least 512 characters; its three measurements cannot characterize long-document p95.

The runner records hardware, framework versions, process CPU time, peak Windows working set and model-loading time. The loading timer begins inside the worker after harness imports; it is not complete process-startup time, and framework imports performed lazily by an adapter are included. Weight sizes exclude tokenizer files and rejected alternate graphs. The failed Windows power-scheme query is retained as unavailable metadata. These are single-machine observations with uncontrolled external background load and power state.
