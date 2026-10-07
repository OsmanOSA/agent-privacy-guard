# Comparaison finale des nouveaux candidats MIT

Modèle retenu pour la détection des personnes : **DistilCamemBERT FP32**.

DistilCamemBERT obtient le meilleur F1 observé sur les deux corpus de personnes : 70,71 % sur Sequoia et 64,69 % sur Europeana. Aucun score global ne mélange ces deux corpus et le diagnostic SoDUCo.
Sa couverture complète des références PERSON atteint 87,04 % sur Sequoia et 86,50 % sur Europeana, supérieure aux trois nouveaux candidats. Pour la pseudonymisation, cette couverture compte autant que les limites exactes des entités.
spaCy et hmBERT Tiny sont plus rapides, mais leur qualité PERSON baisse nettement sur Sequoia. hmBERT Tiny améliore le diagnostic SoDUCo, qui réunit noms et entreprises ; cela ne suffit pas à sélectionner un détecteur de personnes généraliste.
ModernCamemBERT n'améliore pas le F1 observé et reste plus lent dans son déploiement CPU FP32 eager. L'écart de F1 Sequoia avec DistilCamemBERT n'est pas établi par l'intervalle bootstrap apparié ; sur Europeana, cet intervalle favorise DistilCamemBERT. Le choix s'appuie aussi sur la couverture et le coût mesuré.
Les nouvelles latences médianes de DistilCamemBERT sont 11,95 ms sur Sequoia, 80,19 ms sur Europeana et 9,50 ms sur SoDUCo. Son F1 est repris et recalculé à partir des prédictions précédentes, et sa latence est remesurée dans cette série.
La comparaison s'arrête ici. Ce choix ne remplace pas encore le modèle de production et ne démontre pas une couverture complète de tous les types de données personnelles.

## Protocole

Les trois nouveaux modèles utilisent les textes et références figés de la comparaison précédente : 2 084 phrases Sequoia hors Wikipédia, 512 extraits Europeana et 512 entrées SoDUCo. Les limites des annotations et exclusions figurent dans [le rapport des corpus](report-additional-20261006.md). Aucune donnée d'évaluation n'a été générée.

Les seuils des nouveaux modèles sont sélectionnés sur les mêmes 512 exemples de calibration WikiNER et la même grille que la première étude. Aucun seuil n'est réglé sur les trois corpus de test. spaCy fournit des décisions natives sans score de confiance par entité : le score interne 1 est un marqueur technique, et tous les seuils de la grille donnent les mêmes prédictions.

Les prédictions de qualité de DistilCamemBERT sont reprises à l'identique et leur F1 est recalculé. Sa latence est remesurée pendant cette série. Les quatre déploiements passent dans des processus séparés, sur CPU Ryzen 5 5600H, avec quatre threads configurés et un texte à la fois. Les bibliothèques de la première étude gardent leurs versions ; spaCy 3.8.11 et Flair 0.15.1 sont ajoutés uniquement à l'environnement local d'évaluation.

Chaque corpus possède 75 entrées communes de chronométrage, chacune exécutée trois fois après échauffement : 225 observations par modèle et par corpus. L'ordre des modèles tourne entre les passes. Le temps comprend tokenisation, toutes les fenêtres d'inférence et décodage. Il exclut chargement du modèle et cycle du hook. Le p95 est le 95e percentile empirique.

La charge de fond, la température et la fréquence du processeur ne sont pas contrôlées. Les latences de DistilCamemBERT diffèrent donc de la série précédente ; les tableaux utilisent uniquement son contrôle contemporain. Les différences nettes de vitesse entre ces déploiements subsistent, sans attribuer la variation entre séries à une cause non mesurée.

## Résultats

### Sequoia hors Wikipédia

| Modèle | Seuil | Précision % | Rappel % | F1 exact % | Références entièrement couvertes | Faux positifs sur textes négatifs % |
| --- | --- | --- | --- | --- | --- | --- |
| DistilCamemBERT FP32 | 0.5 | 66.45 | 75.56 | 70.71 | 235/270 | 2.69 |
| spaCy multilingue 3.8.0 | 0.6 | 26.84 | 54.07 | 35.87 | 209/270 | 14.44 |
| hmBERT Tiny français FP32 | 0.25 | 36.70 | 61.85 | 46.07 | 167/270 | 10.61 |
| ModernCamemBERT FP32 | 0.6 | 68.12 | 69.63 | 68.86 | 207/270 | 2.32 |

| Modèle | Médiane ms | p95 ms | Observations |
| --- | --- | --- | --- |
| DistilCamemBERT FP32 | 11.95 | 27.93 | 225 |
| spaCy multilingue 3.8.0 | 2.99 | 5.80 | 225 |
| hmBERT Tiny français FP32 | 3.60 | 5.92 | 225 |
| ModernCamemBERT FP32 | 67.70 | 122.52 | 225 |

### Europeana français OCR

| Modèle | Seuil | Précision % | Rappel % | F1 exact % | Références entièrement couvertes | Faux positifs sur textes négatifs % |
| --- | --- | --- | --- | --- | --- | --- |
| DistilCamemBERT FP32 | 0.5 | 61.11 | 68.72 | 64.69 | 1153/1333 | 20.75 |
| spaCy multilingue 3.8.0 | 0.6 | 42.23 | 42.01 | 42.12 | 894/1333 | 41.51 |
| hmBERT Tiny français FP32 | 0.25 | 55.93 | 61.59 | 58.62 | 833/1333 | 33.33 |
| ModernCamemBERT FP32 | 0.6 | 68.11 | 49.51 | 57.34 | 774/1333 | 8.18 |

| Modèle | Médiane ms | p95 ms | Observations |
| --- | --- | --- | --- |
| DistilCamemBERT FP32 | 80.19 | 112.63 | 225 |
| spaCy multilingue 3.8.0 | 11.81 | 14.03 | 225 |
| hmBERT Tiny français FP32 | 8.64 | 11.17 | 225 |
| ModernCamemBERT FP32 | 267.13 | 348.87 | 225 |

### SoDUCo : noms ou entreprises

| Modèle | Seuil | Précision % | Rappel % | F1 exact % | Références entièrement couvertes | Faux positifs sur textes négatifs % |
| --- | --- | --- | --- | --- | --- | --- |
| DistilCamemBERT FP32 | 0.5 | 37.38 | 46.88 | 41.59 | 241/512 | sans objet |
| spaCy multilingue 3.8.0 | 0.6 | 28.11 | 25.59 | 26.79 | 131/512 | sans objet |
| hmBERT Tiny français FP32 | 0.25 | 38.69 | 55.47 | 45.59 | 285/512 | sans objet |
| ModernCamemBERT FP32 | 0.6 | 27.14 | 14.26 | 18.69 | 73/512 | sans objet |

| Modèle | Médiane ms | p95 ms | Observations |
| --- | --- | --- | --- |
| DistilCamemBERT FP32 | 9.50 | 16.39 | 225 |
| spaCy multilingue 3.8.0 | 2.51 | 3.80 | 225 |
| hmBERT Tiny français FP32 | 3.40 | 4.22 | 225 |
| ModernCamemBERT FP32 | 60.92 | 86.32 | 225 |

## Interprétation

SoDUCo réunit personnes et entreprises dans sa référence PER. Les sorties PERSON sont seulement réétiquetées NAME_OR_BUSINESS pour ce diagnostic. Aucun score d'adresse n'est calculé, et les F1 des trois corpus ne sont pas moyennés.

hmBERT Tiny a été entraîné sur ICDAR-Europeana, une variante de notre corpus Europeana : son résultat Europeana est exposé à l'entraînement. Il ne prouve pas une généralisation indépendante. spaCy déclare WikiNER. ModernCamemBERT déclare frenchNER_4entities, qui combine WikiNER, MultiCoNER, MultiNERD et pii-masking-200k. Les corpus de test ne sont pas nommés dans cette dernière liste ; cela ne prouve pas l'absence de tout recoupement de préentraînement.

ModernCamemBERT utilise ses étiquettes IO natives ; elles sont converties en I-PER pour le décodeur commun. Ses fenêtres de 512 tokens se chevauchent de 64 tokens et couvrent tout le texte. La compilation de référence est désactivée et l'attention eager FP32 est utilisée sur CPU. hmBERT conserve son checkpoint Flair, ses phrases longues autorisées et son contexte interphrase désactivé. spaCy conserve son pipeline NER natif. Les différences de vitesse concernent ces déploiements et ne démontrent pas la vitesse intrinsèque des architectures.

Les F1 sont recalculés à partir de toutes les prédictions. Les identifiants et empreintes des sorties chronométrées correspondent aux sorties de qualité, sans divergence. Les intervalles par bootstrap apparié à 1 000 répétitions et les résultats par domaine sont conservés dans le résumé JSON. Les corpus, poids et prédictions restent dans les dossiers locaux ignorés par Git.

Le premier passage ModernCamemBERT s'est arrêté sur SoDUCo : son normaliseur natif supprime 14 glyphes Unicode privés dans 13 entrées. Ces glyphes font partie des références NAME_OR_BUSINESS. Le contrôle distingue maintenant ces suppressions déclarées d'une troncature ; les textes, références et positions restent inchangés, et aucune prédiction n'est étendue pour couvrir artificiellement un glyphe. Un audit de tous les textes et de la calibration confirme zéro suppression sur Sequoia, Europeana et la calibration : leurs sorties complètes sont conservées. Le passage SoDUCo interrompu est repris en entier, puis toutes les latences sont mesurées avec le même code final. Le manifeste conserve les empreintes avant et après reprise. Aucun document n'est exclu à cause de cette normalisation.

## Versions et sources

- [spaCy multilingue 3.8.0](https://github.com/explosion/spacy-models/releases/tag/xx_ent_wiki_sm-3.8.0) : licence MIT déclarée, version `xx_ent_wiki_sm-3.8.0`.
- [hmBERT Tiny français FP32](https://huggingface.co/stefan-it/hmbench-icdar-fr-hmbert_tiny-bs8-wsFalse-e10-lr3e-05-poolingfirst-layers-1-crfFalse-2) : licence MIT déclarée, version `1037ad3af57bc1315fb39c6fdf232f4c3aff5c40`.
- [ModernCamemBERT FP32](https://huggingface.co/CATIE-AQ/Moderncamembert_4entities) : licence MIT déclarée, version `3fbea7e29487a7d357eee64ad0d7ea9313552617`.

Les déclarations MIT et notices disponibles sont conservées avec les artefacts locaux. La licence MIT du dépôt ne remplace pas les licences de ses dépendances.

## Reproduction

```powershell
evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.fetch_mit
evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.run_mit
evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.mit_analysis
evaluation/ner/.venv/Scripts/python.exe -m evaluation.ner.mit_report
```
