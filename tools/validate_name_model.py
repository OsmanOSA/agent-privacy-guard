"""Validates the ONNX name detector against the original GLiNER2 model.

Two checks, on every text of the validation set:
1. Model input: the token ids built without PyTorch equal GLiNER2's, id for id.
2. Result: the same person names at the same character positions.

Runs in the build environment (PyTorch + gliner2), after tools/build_name_model.py:
    python tools/validate_name_model.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from gliner2 import GLiNER2  # noqa: E402
from gliner2.training.trainer import ExtractorCollator  # noqa: E402
from transformers.modeling_utils import no_init_weights  # noqa: E402

from privacy_guard.service.onnx_name_detector import OnnxNameDetector, _split_words  # noqa: E402

PLAYGROUND = PROJECT / "playground"
TEXTS = [
    (PLAYGROUND / "lettre.txt").read_text(encoding="utf-8"),
    (PLAYGROUND / "fiche_client.txt").read_text(encoding="utf-8"),
    "J'ai appelé Jean hier soir, il m'a dit que Sophie Lefèvre passerait demain.",
    "Merci à Karim Benali et à Mme Nguyen pour leur aide sur le projet.",
    "Thomas Girard\nDéveloppeur Python senior\nEncadré par Isabelle Moreau chez Capgemini, Lyon.",
    "Le rapport de Marie-Claire Dubois-Lambert a été validé par le Dr Ahmed El Mansouri.",
    "Paris et Lyon accueillent la conférence ; Orange et Renault la sponsorisent.",
    "Rendez-vous avec Léa, Hugo et Chloé devant la gare Saint-Lazare à 18h.",
    "Le contrat lie la société Durand SARL et M. Pierre Durand, son gérant.",
    "Victor Hugo a écrit Les Misérables ; la rue Victor Hugo est fermée.",
    "Contact: john.smith@example.com, call Emily O'Connor (+1 415 555 0132)!",
    "",
    "Aucun nom ici, seulement du texte ordinaire",
]


def reference_spans(model: GLiNER2, text: str) -> set[tuple[int, int]]:
    result = model.extract_entities(text, ["person"], threshold=0.5, include_spans=True)
    return {(e["start"], min(e["end"], len(text))) for e in result["entities"]["person"]}


def reference_ids(collator: ExtractorCollator, text: str) -> list[int]:
    return collator([(text, {"entities": {"person": ""}})]).input_ids[0].tolist()


def main() -> int:
    with no_init_weights():
        model = GLiNER2.from_pretrained("fastino/gliner2-privacy-filter-PII-multi").eval()
    collator = ExtractorCollator(model.processor, is_training=False, architecture=model.architecture)
    detector = OnnxNameDetector()

    failures = 0
    for text in TEXTS:
        ours_ids, _ = detector._model_input(_split_words(text))
        if ours_ids != reference_ids(collator, text):
            failures += 1
            print(f"INPUT MISMATCH on {text[:40]!r}")

        expected = reference_spans(model, text)
        got = {(f.start, f.end) for f in detector.find_names(text)}
        if got != expected:
            failures += 1
            print(f"RESULT MISMATCH on {text[:40]!r}\n  gliner2: {sorted(expected)}\n  onnx   : {sorted(got)}")

    print(f"{len(TEXTS) - failures}/{len(TEXTS)} texts identical" if failures == 0 else f"{failures} mismatch(es)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
