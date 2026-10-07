# Commercial reuse of model artifacts

Active candidates declare MIT or Apache 2.0 for their model repositories. These permissive licenses support modification, redistribution and commercial use subject to their terms. The project code stays MIT; third-party weights, tokenizers and runtimes retain their own licenses. Downstream users need the same upstream licenses and notices that we receive.

## Accepted candidates

| Model | Weight declaration | Evidence and remaining distribution work |
| --- | --- | --- |
| GLiNER2 PII | Apache 2.0 | Pinned model card; no separate LICENSE file in that revision. Trace the existing ONNX export to its source checkpoint and preserve upstream notices. |
| Masker Mini | Apache 2.0 | Pinned LICENSE and NOTICE files are present. Retain NOTICE and the MIT notices for the Microsoft base weights and tokenizer named there. |
| Nym multilingual small | MIT | Pinned model card; no separate LICENSE file in that revision. Preserve the mmBERT-small base-model license and identify the applicable copyright notices. |
| DistilCamemBERT NER | MIT | Pinned model card; no separate LICENSE file in that revision. The evaluation uses the upstream FP32 ONNX graph; retain DistilCamemBERT/CamemBERT notices. |
| GLiNER multilingual PII v1 | Apache 2.0 | Pinned model card; no separate LICENSE file in that revision. Include the license and identify base encoder, tokenizer and copyright notices. |

The model cards identify the declared license; they are not proof that every upstream right was cleared. `license-evidence.json` records the exact revision URLs and hashes of the declarations. Raw evidence is stored locally under the ignored `data/license-evidence/` directory. Evaluation eligibility does not mark an artifact ready for product redistribution: `candidates.json` records that remaining work separately.

The published [Masker NOTICE](https://huggingface.co/divergentlabs/masker-mini/blob/beb7235d454aa4488b6ee1cd47f417caa12a6d15/NOTICE) identifies Microsoft mDeBERTa-v3 and Multilingual MiniLM derivatives and lists training-data licenses separately. Those source-data licenses are not replaced by the weight license. Further training requires permission for the new training corpus as well.

## License terms to preserve

[MIT](https://opensource.org/license/mit) permits use, modification, redistribution and sale, and requires retention of its copyright and permission notice. [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) also permits commercial reuse; redistribution requires a license copy, relevant copyright and attribution notices, notices of modified files and any applicable NOTICE content. It includes an express contributor patent grant within its stated scope. Neither license grants trademark rights or guarantees the absence of third-party claims.

MIT project code can coexist with Apache-licensed model components, while those components continue to carry Apache notices. Do not relabel upstream Apache weights as entirely MIT. Converting weights to ONNX, quantizing them or fine-tuning them does not remove their upstream obligations. A distributed model package should identify its origin and modifications and contain the applicable licenses and notices for both weights and tokenizer.

ONNX Runtime declares MIT, tokenizers declares Apache 2.0, and NumPy has BSD-based and other bundled permissive notices. The installed runtime inventory records versions and available notice hashes. Future deployment must include licenses for the actual distributed dependencies, including their bundled third-party components; this inventory is not an assertion about dependencies not yet installed.

`evaluation-runtime-licenses.json` separately inventories the actual research environment, including PyTorch, GLiNER, Transformers and the ONNX inspection package. It records declarations and available wheel notice hashes. Research dependencies are installed only under `evaluation/ner/.venv`; this does not add them to the production package. Missing wheel metadata remains an inventory limitation, not a license waiver.

## Excluded candidates and data

[Rampart](https://huggingface.co/nationaldesignstudio/rampart/blob/main/LICENSE) is CC BY 4.0. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) permits commercial use and modification with attribution, a license link and change indications. We exclude it to keep active weights within our narrower MIT/Apache/BSD software-license preference. This is a selection policy, not a finding that Rampart forbids commercialization.

The French spaCy model weights declare LGPL-LR, while the spaCy library uses a different license. We exclude those weights to avoid their different redistribution obligations. A copyleft license does not inherently prohibit commercial use.

WikiNER-fr-gold declares CC BY 4.0. Keep its source attribution and corpus terms; the corpus is not included in the distributed product. Its license is separate from our code license.

The [FENEC source table](https://github.com/alicemillour/FENEC/tree/3a975635d57712096d8ebf859d842042c782837b) identifies the selected texts as CC BY 2.5 (Wikinews), CC BY-SA 2.0 (L'Est Républicain) and CC BY-SA 4.0 (UD French GSD and Rhapsodie). These licenses permit commercial use with attribution; share-alike applies to distributed adaptations of the affected data. This study uses inference only and keeps source texts and prepared corpora outside the code and product bundle. It does not train models on these documents or relicense the data as MIT. Credit Alice Millour, Yoann Dupont, Alexane Jouglar and Karën Fort for FENEC, their [2022 corpus paper](https://aclanthology.org/2022.jeptalnrecital-taln.8/), and the source authors named in its table. See [CC BY 2.5](https://creativecommons.org/licenses/by/2.5/), [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/) and [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) for the conditions.

HIPE declares CC BY NC SA 4.0. The [non-commercial clause](https://creativecommons.org/licenses/by-nc-sa/4.0/) does not authorize use primarily directed toward commercial advantage. Keeping a dataset out of a product archive alone does not authorize a commercial-purpose benchmark. HIPE is therefore inactive for fetching, preparation and scoring until a separate permission or eligible replacement is obtained. Existing local downloads remain ignored and are not redistributed.

Models or datasets restricted to research-only, non-commercial or no-derivatives use do not meet this project goal. Custom or missing license declarations remain outside automatic eligibility. Permissive licensing supports the intended business use; satisfying its conditions still requires accurate provenance and preserved notices.

## Additional local evaluation corpora

The added datasets are used only to measure and select models. No corpus is bundled with the product and no model is trained on these texts. Dataset licensing remains distinct from the permissive-weight policy.

The original Europeana Newspapers repository declares CC0. SoDUCo licenses its transformed text and annotations under CC BY 4.0; its original Gallica images have separate rights and are not used in this study. Deep Sequoia's LGPL-LR permits running programs using the resource; it is eligible for local inference, while copying or redistributing corpus derivatives has separate conditions. This data eligibility does not make LGPL-LR model weights eligible under the model shortlist policy. AjMC is kept inactive pending clarification of its conflicting CC BY and noncommercial notices. See [the pinned source audit](additional-datasets.md).
