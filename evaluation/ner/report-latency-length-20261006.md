# DistilCamemBERT : coût d'une lecture longue

La première analyse d'environ 4 000 tokens prend **2,45 secondes** dans le déploiement CPU évalué. Les latences de quelques millisecondes obtenues sur des phrases courtes ne décrivent donc pas le coût d'un document long. La sélection précédente établissait un compromis de qualité entre les modèles ; elle ne validait pas encore la latence du workflow complet.

| Tokens du détecteur | Caractères | Fenêtres | Médiane | Minimum–maximum |
| ---: | ---: | ---: | ---: | ---: |
| 498 | 1 775 | 1 | 270 ms | 267–276 ms |
| 999 | 3 617 | 3 | 606 ms | 606–619 ms |
| 1 999 | 7 495 | 5 | 1 224 ms | 1 219–1 252 ms |
| 3 997 | 14 792 | 9 | 2 446 ms | 2 418–2 521 ms |

## Mesure

Les quatre entrées sont des préfixes contigus du même texte OCR français publié par Europeana, reconstitué avec une espace entre les tokens de la source. Aucune phrase fictive ni répétition artificielle n'a été ajoutée. Ces extraits ne sont pas des pages originales : le format publié ne conserve pas leurs limites ni leurs espaces. Leur longueur est comptée par le tokenizer de DistilCamemBERT, sans les tokens spéciaux ; elle ne donne pas directement le nombre de tokens de Claude.

Chaque entrée a un passage de chauffe puis cinq mesures. L'ordre des longueurs alterne entre croissant et décroissant. Le modèle ONNX FP32 reste chargé, avec quatre threads CPU et un batch de un, sur le même Ryzen 5 5600H que les comparaisons précédentes. La durée comprend la tokenisation, l'inférence de toutes les fenêtres et le décodage des entités. Les fenêtres contiennent au plus 512 tokens spéciaux compris, avec un chevauchement de 64 tokens. Elles sont exécutées successivement.

Le chargement, la lecture du fichier, la communication avec le service, le coffre et la pseudonymisation sont exclus. Aucun cache de prédictions n'intervient. Les empreintes des prédictions sont identiques entre la chauffe et les cinq passages de chaque entrée. Les résultats bruts, empreintes des artefacts, de la source et du code sont conservés dans [latency-length-20261006.json](latency-length-20261006.json). Le programme de mesure est [latency_length.py](latency_length.py).

Il s'agit d'une mesure de latence sur une seule séquence source, et non d'une nouvelle évaluation de F1 ou d'une distribution représentative de tous les documents. Cinq mesures justifient une médiane et une étendue observée, pas une estimation robuste du p95. La charge concurrente, la température et la fréquence CPU ne sont pas contrôlées.

## Conséquence pour l'intégration

Le modèle retenu reste un candidat de qualité ; ce résultat ne permet pas de promettre une première lecture de plusieurs milliers de tokens en quelques millisecondes.

Le service existant charge déjà son détecteur une fois. Cette organisation peut accueillir le modèle retenu, mais ne supprime pas le coût de l'inférence. Une optimisation à envisager est de réutiliser les positions des entités lorsque le texte est strictement identique, avec une clé incluant son empreinte, la version du modèle et les paramètres de détection. La pseudonymisation doit toujours s'appliquer à chaque lecture, avec le coffre de la session courante. Un document modifié doit être réanalysé. Le découpage pour ne recalculer que les passages modifiés demanderait ensuite une gestion du contexte et des limites, avec une vérification de la qualité.

La réutilisation ne réduit pas le coût d'une première lecture inédite. Le batching ou une quantification pourraient être examinés séparément, mais aucun gain ni maintien de qualité n'a été démontré ici. Le graphe quantifié amont précédemment rejeté reste exclu. Cette mesure ne modifie pas le hook de production.
