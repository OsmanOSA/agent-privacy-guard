"""Write explicit French quality and latency tables from validated results."""

import json

from .fetch import BASE

NAMES = {"distilcamembert-base-ner": "DistilCamemBERT FP32",
    "spacy-multilingual": "spaCy multilingue 3.8.0", "hmbert-tiny-fr": "hmBERT Tiny français FP32",
    "moderncamembert-fr": "ModernCamemBERT FP32"}
DATASETS = {"deep-sequoia-nonwiki": "Sequoia hors Wikipédia",
    "europeana-newspapers-fr": "Europeana français OCR", "soduco-nested-ner": "SoDUCo : noms ou entreprises"}


def pct(value):
    return "sans objet" if value is None else f"{100 * value:.2f}"


def main():
    summary = json.loads((BASE / "summary-mit-20261006.json").read_text(encoding="utf-8"))
    selection = json.loads((BASE / "mit-selection.json").read_text(encoding="utf-8"))
    registry = json.loads((BASE / "mit-candidates.json").read_text(encoding="utf-8"))
    lines = ["# Comparaison finale des nouveaux candidats MIT", "",
        f"Modèle retenu pour la détection des personnes : **{NAMES[selection['selected_model']]}**.", "",
        *selection["reasons"], "", "## Protocole", "",
        "Les trois nouveaux modèles utilisent les textes et références figés de la comparaison précédente : 2 084 phrases Sequoia hors Wikipédia, 512 extraits Europeana et 512 entrées SoDUCo. Les limites des annotations et exclusions figurent dans [le rapport des corpus](report-additional-20261006.md). Aucune donnée d'évaluation n'a été générée.", "",
        "Les seuils des nouveaux modèles sont sélectionnés sur les mêmes 512 exemples de calibration WikiNER et la même grille que la première étude. Aucun seuil n'est réglé sur les trois corpus de test. spaCy fournit des décisions natives sans score de confiance par entité : le score interne 1 est un marqueur technique, et tous les seuils de la grille donnent les mêmes prédictions.", "",
        "Les prédictions de qualité de DistilCamemBERT sont reprises à l'identique et leur F1 est recalculé. Sa latence est remesurée pendant cette série. Les quatre déploiements passent dans des processus séparés, sur CPU Ryzen 5 5600H, avec quatre threads configurés et un texte à la fois. Les bibliothèques de la première étude gardent leurs versions ; spaCy 3.8.11 et Flair 0.15.1 sont ajoutés uniquement à l'environnement local d'évaluation.", "",
        "Chaque corpus possède 75 entrées communes de chronométrage, chacune exécutée trois fois après échauffement : 225 observations par modèle et par corpus. L'ordre des modèles tourne entre les passes. Le temps comprend tokenisation, toutes les fenêtres d'inférence et décodage. Il exclut chargement du modèle et cycle du hook. Le p95 est le 95e percentile empirique.", "",
        "La charge de fond, la température et la fréquence du processeur ne sont pas contrôlées. Les latences de DistilCamemBERT diffèrent donc de la série précédente ; les tableaux utilisent uniquement son contrôle contemporain. Les différences nettes de vitesse entre ces déploiements subsistent, sans attribuer la variation entre séries à une cause non mesurée.", "",
        "## Résultats", ""]
    for dataset, title in DATASETS.items():
        lines += [f"### {title}", "",
            "| Modèle | Seuil | Précision % | Rappel % | F1 exact % | Références entièrement couvertes | Faux positifs sur textes négatifs % |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
        for name, model in summary["models"].items():
            q = model["datasets"][dataset]["quality"]
            lines.append(f"| {NAMES[name]} | {model['threshold']} | {pct(q['exact_precision'])} | {pct(q['exact_recall'])} | {pct(q['exact_f1'])} | {q.get('fully_covered_entities', 0)}/{q['gold_entities']} | {pct(q['negative_record_false_positive_rate'])} |")
        lines += ["", "| Modèle | Médiane ms | p95 ms | Observations |", "| --- | --- | --- | --- |"]
        for name, model in summary["models"].items():
            timing = model["datasets"][dataset]["latency_ms"]
            lines.append(f"| {NAMES[name]} | {timing['p50']:.2f} | {timing['p95']:.2f} | {timing['observations']} |")
        lines.append("")
    lines += ["## Interprétation", "",
        "SoDUCo réunit personnes et entreprises dans sa référence PER. Les sorties PERSON sont seulement réétiquetées NAME_OR_BUSINESS pour ce diagnostic. Aucun score d'adresse n'est calculé, et les F1 des trois corpus ne sont pas moyennés.", "",
        "hmBERT Tiny a été entraîné sur ICDAR-Europeana, une variante de notre corpus Europeana : son résultat Europeana est exposé à l'entraînement. Il ne prouve pas une généralisation indépendante. spaCy déclare WikiNER. ModernCamemBERT déclare frenchNER_4entities, qui combine WikiNER, MultiCoNER, MultiNERD et pii-masking-200k. Les corpus de test ne sont pas nommés dans cette dernière liste ; cela ne prouve pas l'absence de tout recoupement de préentraînement.", "",
        "ModernCamemBERT utilise ses étiquettes IO natives ; elles sont converties en I-PER pour le décodeur commun. Ses fenêtres de 512 tokens se chevauchent de 64 tokens et couvrent tout le texte. La compilation de référence est désactivée et l'attention eager FP32 est utilisée sur CPU. hmBERT conserve son checkpoint Flair, ses phrases longues autorisées et son contexte interphrase désactivé. spaCy conserve son pipeline NER natif. Les différences de vitesse concernent ces déploiements et ne démontrent pas la vitesse intrinsèque des architectures.", "",
        "Les F1 sont recalculés à partir de toutes les prédictions. Les identifiants et empreintes des sorties chronométrées correspondent aux sorties de qualité, sans divergence. Les intervalles par bootstrap apparié à 1 000 répétitions et les résultats par domaine sont conservés dans le résumé JSON. Les corpus, poids et prédictions restent dans les dossiers locaux ignorés par Git.", "",
        "Le premier passage ModernCamemBERT s'est arrêté sur SoDUCo : son normaliseur natif supprime 14 glyphes Unicode privés dans 13 entrées. Ces glyphes font partie des références NAME_OR_BUSINESS. Le contrôle distingue maintenant ces suppressions déclarées d'une troncature ; les textes, références et positions restent inchangés, et aucune prédiction n'est étendue pour couvrir artificiellement un glyphe. Un audit de tous les textes et de la calibration confirme zéro suppression sur Sequoia, Europeana et la calibration : leurs sorties complètes sont conservées. Le passage SoDUCo interrompu est repris en entier, puis toutes les latences sont mesurées avec le même code final. Le manifeste conserve les empreintes avant et après reprise. Aucun document n'est exclu à cause de cette normalisation.", "",
        "## Versions et sources", ""]
    for item in registry["models"]:
        lines.append(f"- [{NAMES[item['id']]}]({item['source']}) : licence MIT déclarée, version `{item['revision']}`.")
    lines += ["", "Les déclarations MIT et notices disponibles sont conservées avec les artefacts locaux. La licence MIT du dépôt ne remplace pas les licences de ses dépendances.", "",
        "## Reproduction", "", "```powershell",
        "evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.fetch_mit",
        "evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.run_mit",
        "evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.mit_analysis",
        "evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.mit_report", "```", ""]
    (BASE / "report-mit-20261006.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote report-mit-20261006.md")


if __name__ == "__main__":
    main()
