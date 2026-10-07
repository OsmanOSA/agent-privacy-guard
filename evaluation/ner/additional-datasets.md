# Four additional French entity annotation datasets

Deep Sequoia, SoDUCo, Europeana Newspapers and AjMC provide French text with human entity annotations from sources other than WikiNER. Deep Sequoia is the best next source for a contemporary PERSON comparison. SoDUCo is especially useful for addresses and noisy structured records. Europeana and AjMC test historical French and OCR robustness.

Three sources have licenses permitting local commercial evaluation under their respective terms. AjMC has conflicting license notices and remains on hold. A [separate completed evaluation](report-additional-20261006.md) now compares the five deployments on these three sources. The original WikiNER comparison remains unchanged.

## Selection

| Dataset and selected version | French material inspected | Reference labels | Local commercial evaluation |
| --- | --- | --- | --- |
| [Deep Sequoia 9.2](https://deep-sequoia.inria.fr/) with the PARSEME-FR layer | 3,099 sentences; 2,103 after excluding the 996 Wikipedia sentences | Typed named entities, including PERSON, LOCATION and ORGANIZATION, plus MWE annotations | LGPL-LR; permitted for inference, with license conditions for copying and redistribution |
| [SoDUCo nested NER v2](https://zenodo.org/records/8167628), derived from FTD | 8,765 directory entries from 18 French trade directories and 78 pages | Names, addresses, streets, numbers, activities and titles; manually corrected reference text and human annotations | CC BY 4.0 for derived text and annotations; original Gallica images have separate conditions |
| [Europeana Newspapers French](https://github.com/EuropeanaNewspapers/ner-corpora) | 205,916 token rows in the French BnF IO export | PER, LOC and ORG, annotated on historical newspaper OCR | CC0 in the original repository |
| [AjMC original v0.4](https://github.com/AjaxMultiCommentary/AjMC-NE-corpus) | Inspected French test export: 15 page documents and 3,053 token rows | Coarse and fine person labels, locations, works, dates and bibliographic scopes | Hold: CC BY 4.0 in the article and README license section, but CC BY-NC-SA 4.0 in its dataset-profile badge |

Counts above describe the downloaded artifacts. They are not scores or guarantees of annotation completeness. Source links, revisions, hashes and exclusions are recorded in `additional-datasets.json`. Raw artifacts are stored under the Git-ignored `data/additional-20261006/` directory.

## Deep Sequoia

The official 9.2 archive contains `sequoia-ud.parseme.frsemcor`, with twelve columns. Column 11 contains typed PARSEME-FR annotations such as `NE-PERS.final`. Column 12 contains noun supersenses; a supersense such as `Person` is not a named-person gold annotation. The plain UD export and the six-column FrSemCor export must not replace the typed NE layer.

The inspected file has 524 Est Republicain sentences, 561 Europarl sentences, 574 EMEA development sentences, 444 EMEA test sentences and 996 Wikipedia sentences. This gives 2,103 non-Wikipedia sentences. Typed PERSON annotation starts number 272 outside Wikipedia: 167 in Est Republicain, 73 in Europarl and 32 in EMEA test. These are structural counts before validation of overlap, discontinuity and span reconstruction.

For the next evaluation, retain non-Wikipedia sources and report each domain separately. Check Est Republicain text overlap with the existing FENEC control. Include EMEA as a negative-heavy domain rather than letting it dominate a pooled PERSON score. Recover spans from the entity identifiers and original text; do not flatten a discontinuous entity into a continuous interval without documenting that convention.

The [LGPL-LR license](https://deep-sequoia.inria.fr/licence/) permits running programs using the resource. Local inference and content-free aggregate scores do not require treating the product code as a redistributed corpus. Copies and modified corpus distributions retain their own notices and license obligations. This does not change the policy for model weights.

## SoDUCo and French Trade Directories

The inspected v2 JSON has 8,765 entries, including corrected text in `text_ocr_ref` and nested reference annotations in `nested_ner_xml_ref`. The `has_valid_ner_xml_pero` flag is true for 8,445 entries; use that matched subset for a paired clean-text versus OCR comparison. The remaining 320 entries must not be silently included in the aligned OCR task.

The [authors' paper](https://arxiv.org/html/2302.10204) defines `PER` as person(s) **or business name**, and `SPAT` as an address containing nested street and number annotations. A direct `PER → PERSON` mapping would mislabel businesses and distort our person-only comparison. Use SoDUCo for a separate name-or-business task, address coverage and OCR robustness. A PERSON-only task requires an existing finer reference layer; do not invent a new gold distinction by filtering model predictions.

The JSON has 8,772 `PER` opening tags and 8,985 `SPAT` opening tags across the complete corrected-text set. These are annotation counts, not counts of uniquely named individuals or unique addresses. Flat FTD and nested SoDUCo versions share source entries and count as one corpus family.

The publisher explicitly licenses transformed text and annotations under CC BY 4.0. Its description separately identifies restrictions on original Gallica images. Use the text/annotation JSON for this study, with attribution; do not infer that its license covers the original scans.

## Europeana Newspapers

The original repository declares CC0 and describes human annotation of OCR text. Its French export contains only `I-PER`, `I-LOC`, `I-ORG` and `O` labels, rather than explicit begin tags. It contains 5,667 PER-tagged tokens, which must not be described as 5,667 person mentions. Two literal hash-sign tokens also belong to the corpus; they are not metadata comments.

The authors warn about OCR errors, removal of noisy sentence fragments during post-processing and possible effects on evaluation. Treat it as an OCR stress corpus. Validate sentence boundaries and entity reconstruction before producing an exact-span score; IO tags cannot recover the boundary between directly adjacent same-type entities. Keep its results separate from clean contemporary French.

## AjMC

The [dataset article](https://openhumanitiesdata.metajnl.com/articles/10.5334/johd.150) describes independent annotation, curator review and the v0.4 release under CC BY 4.0. The downloaded README license section agrees, and the inspected French test file has `CC-BY` metadata. However, the README dataset-profile badge links to CC BY-NC-SA 4.0. Until these conflicting notices are resolved, the manifest does not authorize product-oriented model evaluation on this source.

The French test export has 81 coarse person annotation starts: 46 authors, 15 editors, 12 other persons and 8 mythological entities. Its main text is historical French commentary with quotations and abbreviations; it is not a collection of contemporary private documents. Report mythological entities separately if the task is identifying real people. Existing literary material is used as published; no evaluation text or personal value was generated.

The inspected test file has 3,053 token rows, whereas the article's French test table reports 5,391 tokens. Use artifact-derived counts and inspect the release history before reproducing the published benchmark. Do not silently substitute the HIPE-2022 bundle: that distribution explicitly carries a noncommercial license.

## Training exposure and evaluation plan

These corpus families are not renamed WikiNER partitions. That removes the known direct WikiNER source bias for the retained material, but it does not prove that every model has never seen the texts during pretraining, fine-tuning or distillation. Recheck each model's declared sources and deduplicate available corpus texts. Record remaining exposure as unknown.

Start with non-Wikipedia Deep Sequoia for the shared PERSON task. Add Europeana as a separate historical/OCR task and SoDUCo as separate address and name-or-business tasks. AjMC remains a reserve pending its license and artifact-count discrepancies. Preserve existing model artifacts and thresholds for the first transferred-threshold comparison; any new calibration must use a separate published development partition or a frozen source-aware split.

Report per-corpus exact precision, recall and F1, complete mention coverage, partial misses and false positives. Measure latency on the same full inputs for every applicable model and describe input length, hardware, warm-up and percentiles. Use sentence, document or page grouping appropriate to the source for uncertainty intervals and deduplication. Do not pool these incompatible categories into a single leaderboard.

Other investigated sources were not added: MSNER's manually annotated French test is noncommercial; MultiCoNER v2 has automatically produced annotations and Wikipedia-derived text; REDFM validates relations but cannot be assumed to contain exhaustive human gold PERSON annotations. These limitations matter more than reaching an arbitrary corpus count.
