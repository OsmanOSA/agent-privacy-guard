"""Evaluation on PIIMB, the public PII Masking Benchmark (huggingface.co/datasets/piimb).

Puts Privacy Guard on the same scale as ~35 published models (Presidio, GLiNER2,
OpenAI Privacy Filter...). The data is CC BY-NC 4.0: it is downloaded to
~/.privacy-guard/eval/piimb and never committed to this repository.

Run with the model environment: `<model-env python> -m benchmark.piimb [--per-task N]`.
"""
