# OCR and binary document extraction

Tracking: [GitHub issue #1](https://github.com/OsmanOSA/agent-privacy-guard/issues/1).

Deferred beyond the Windows installer milestone. Current protection inspects text
returned by tools; recognizing a document extension is not an extraction guarantee.

Scope: scanned PDFs, images, and native extraction from PDF, DOC/DOCX, ODT and MSG.
Do not add OCR to source-code reads or silently send documents to an external API.

Acceptance criteria:

- Select local extractors and OCR engines with documented redistribution terms.
- Evaluate French documents against annotated references; report recall, precision,
  F1, extraction failures, CPU latency and memory separately.
- Preserve page/region provenance, Unicode offsets and reading order.
- Define behavior for encrypted, malformed, oversized and partly readable files.
- Demonstrate protection before extracted content enters model context, including
  rereads, tool failures and mixed text/image documents.
- Document which formats and agent paths have actually been tested.

Do not count a text-only hook test as evidence of image protection.
