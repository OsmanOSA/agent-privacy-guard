# PRD — Privacy Layer universelle pour agents IA

> **Note de cadrage — 5 octobre 2026.** Ce document conserve la vision initiale, les pistes commerciales et les fonctionnalités envisagées ; il ne décrit pas une couverture validée. Le premier connecteur est volontairement Claude Code ; l'implémentation du coffre cible actuellement Windows. Codex, les autres agents et les autres systèmes viendront ensuite. Le périmètre de livraison actuel, les garanties visées et les critères de validation sont définis dans [docs/product.md](docs/product.md), [docs/architecture.md](docs/architecture.md) et [docs/security/threat-model.md](docs/security/threat-model.md). Ces documents priment pour les contributions et les annonces de compatibilité.

**Nom de travail :** Agent Privacy Guard  
**Version :** 0.1  
**Statut :** Concept / Pre-MVP  
**Plateformes initiales :** macOS  
**Agents initiaux :** Codex, Claude Code  
**Modèle :** local-first, install once, paiement unique envisagé

---

# 1. Résumé produit

Agent Privacy Guard est une couche locale de protection des données destinée aux utilisateurs d’agents IA de développement.

Le produit s’installe une seule fois sur l’ordinateur et s’intègre automatiquement aux agents compatibles.

Son rôle est d’intercepter les informations susceptibles d’être transmises à un modèle distant, de détecter localement les données sensibles, puis de :

- laisser passer les données non sensibles ;
- pseudonymiser les informations personnelles utiles au raisonnement ;
- masquer ou bloquer les secrets qui ne doivent jamais être vus par le modèle ;
- conserver localement et de manière sécurisée les correspondances nécessaires ;
- restaurer les valeurs originales lorsque le résultat revient sur la machine de l’utilisateur.

L’objectif est que l’utilisateur puisse continuer à travailler normalement avec Codex, Claude Code ou d’autres agents sans devoir réfléchir en permanence aux données contenues dans ses fichiers.

---

# 2. Problème

Les agents IA disposent progressivement d’un accès important à l’environnement local :

- code source ;
- fichiers personnels ;
- PDF ;
- documents Word ;
- images ;
- fichiers `.env` ;
- résultats de commandes ;
- logs ;
- bases de données ;
- outils MCP ;
- répertoires complets.

Un utilisateur peut ainsi demander :

> « Prends mon ancien CV et crée-en une meilleure version. »

Le fichier peut contenir :

- nom et prénom ;
- téléphone ;
- adresse ;
- email ;
- date de naissance ;
- identifiants ;
- autres informations personnelles.

L’agent n’a pourtant pas besoin de connaître l’identité réelle de la personne pour accomplir la majorité du travail.

Même problème avec du code :

```text
DATABASE_URL=...
STRIPE_SECRET_KEY=...
OPENAI_API_KEY=...
```

Le programme local peut avoir besoin de ces valeurs.

Le modèle distant, lui, n’en a généralement pas besoin.

La plupart des utilisateurs ne vont cependant ni examiner chaque fichier avant de le donner à l’agent, ni configurer manuellement un système de redaction pour chaque projet.

---

# 3. Vision

Créer une protection suffisamment transparente pour que l’utilisateur puisse l’oublier.

Après installation :

```text
Codex       → Protected
Claude Code → Protected
```

L’utilisateur ne doit pas modifier sa manière de travailler.

Il continue à écrire :

> « Analyse ce document. »

> « Regarde les logs. »

> « Corrige cette configuration. »

> « Transforme mon ancien CV. »

La protection s’applique automatiquement.

Principe fondamental :

**Tout ce que l’agent va chercher lui-même sur la machine (fichier lu, sortie de commande, résultat MCP) passe par PrivacyCore avant d’être envoyé au modèle.**

Ce principe s’applique aux agents supportés par un adapter. Il ne couvre pas le prompt écrit par l’utilisateur (voir §15).

---

# 4. Proposition de valeur

## Pour l’utilisateur

**Install once. Your AI agent reads your files, not your private data.**

Pas de configuration projet par projet.

Pas de cloud supplémentaire.

Pas de compte obligatoire.

Pas d’upload vers notre infrastructure.

Pas de modification des fichiers originaux.

Pas d’abonnement nécessaire dans le modèle commercial initial.

---

# 5. Utilisateurs cibles

## Cible principale

Développeurs utilisant quotidiennement :

- Codex ;
- Claude Code ;
- autres coding agents à terme.

Typiquement indépendants, étudiants, consultants, développeurs salariés ou créateurs de produits.

## Cible secondaire

Utilisateurs techniques employant les agents de code pour manipuler également :

- CV ;
- contrats ;
- factures ;
- exports CSV ;
- documents administratifs ;
- notes ;
- données clients ;
- documents professionnels.

## Hors cible initiale

- DLP d’entreprise complet ;
- conformité réglementaire centralisée ;
- SOC/SIEM ;
- infrastructures avec milliers d’employés ;
- remplacement d’un gestionnaire de secrets.

---

# 6. Principes produit

### Local-first

La détection, la pseudonymisation et le stockage des correspondances doivent fonctionner localement.

### Invisible by default

Une requête ne contenant rien de sensible doit traverser le système avec une latence presque imperceptible.

### Aucun changement de workflow

L’utilisateur ne doit pas appeler manuellement :

```text
privacy-scan document.pdf
```

avant de demander son travail à Codex.

L’intégration le fait automatiquement.

### Original intact

Le produit ne modifie jamais automatiquement le document source.

Il crée une représentation temporaire protégée.

### Fail closed pour les secrets critiques

Pour certaines catégories :

- clés privées ;
- API keys ;
- cartes bancaires ;
- credentials ;
- mots de passe ;

en cas de doute important, le produit privilégie le blocage à l’envoi.

### Réversibilité contrôlée

Les informations pseudonymisées peuvent être restaurées uniquement localement.

---

# 7. Architecture générale

```text
                 ENVIRONNEMENT LOCAL

                       Agent
              Codex / Claude / ...
                         │
                         ▼
                Agent Adapter
                         │
                         ▼
                ┌────────────────┐
                │  PrivacyCore   │
                └───────┬────────┘
                        │
            ┌───────────┼────────────┐
            │           │            │
            ▼           ▼            ▼
        Detector      Policy      Token Vault
            │          Engine         │
            │           │             │
            └───────────┼─────────────┘
                        │
                        ▼
                Protected content
                        │
                        ▼
                  Remote LLM
                        │
                        ▼
                   Response
                        │
                        ▼
                   PrivacyCore
                        │
                        ▼
                    Restore
                        │
                        ▼
                  Local output
```

---

# 8. Composants

## 8.1 PrivacyCore

Moteur indépendant des agents.

API logique :

```text
inspect(content)
transform(content, policy)
restore(content, context)
```

PrivacyCore ne doit connaître ni Codex ni Claude.

Les agents sont gérés par des adapters.

---

# 8.2 Agent Adapters

Chaque agent possède un petit adapter.

```text
adapters/
    codex/
    claude/
    future-agent/
```

L’adapter utilise la méthode d’interception la plus forte disponible pour l’environnement concerné :

- hooks lifecycle ;
- interception des tool calls ;
- gateway local lorsque possible ;
- wrapper d’exécution ;
- autres mécanismes natifs.

La modification d’une API d’agent ne doit pas nécessiter de modifier PrivacyCore.

---

# 8.3 Fast Scanner

Première couche extrêmement rapide.

Détecte notamment :

- emails ;
- URLs avec credentials ;
- IP sensibles selon configuration ;
- numéros de téléphone ;
- cartes bancaires ;
- IBAN ;
- API keys ;
- JWT ;
- private keys ;
- database URLs ;
- tokens connus ;
- mots de passe suivant patterns.

Les règles simples utilisent prioritairement :

- regex ;
- checksums ;
- entropie ;
- formats connus.

---

# 8.4 PII Detector

Deuxième couche destinée aux informations nécessitant davantage de contexte :

- personnes ;
- adresses postales ;
- organisations lorsqu’elles sont configurées comme sensibles ;
- données administratives ;
- autres entités personnalisées.

Le modèle doit fonctionner localement.

Aucune PII n’est envoyée à un LLM externe afin de décider si elle constitue une PII.

---

# 8.5 Policy Engine

Chaque catégorie reçoit une politique.

Exemple :

```yaml
person:
  action: pseudonymize

email:
  action: pseudonymize

phone:
  action: pseudonymize

address:
  action: pseudonymize

credit_card:
  action: block

api_key:
  action: block

private_key:
  action: block

database_credentials:
  action: block
```

Actions initiales :

- `allow`
- `pseudonymize`
- `mask`
- `block`

Action future :

- `ask`

---

# 9. Tokenisation

Exemple :

```text
Jean Dupont
→ ⟦PERSON:91A7⟧

jean@example.com
→ ⟦EMAIL:F48C⟧
```

PrivacyCore conserve :

```text
⟦PERSON:91A7⟧ → Jean Dupont
⟦EMAIL:F48C⟧  → jean@example.com
```

Le modèle ne reçoit que les tokens.

Les occurrences identiques doivent rester cohérentes à l’intérieur d’un même contexte.

Exemple :

```text
Jean Dupont travaille avec Jean Dupont.
```

devient :

```text
⟦PERSON:91A7⟧ travaille avec ⟦PERSON:91A7⟧.
```

Deux personnes différentes ne doivent jamais recevoir le même token.

---

# 10. Token Vault

Le mapping permettant la restauration reste uniquement sur l’ordinateur.

Exigences :

- chiffrement au repos ;
- clé stockée via le mécanisme sécurisé de l’OS ;
- aucune synchronisation cloud par défaut ;
- suppression automatique des mappings temporaires ;
- isolation par session/workspace.

Modes envisagés :

### Session

Mappings supprimés après la session.

### Workspace

Mappings réutilisables pour un projet.

Mode par défaut du MVP : **Session**.

---

# 11. Protection du code et des secrets

Exemple :

```env
DATABASE_URL=postgres://admin:secret@production
STRIPE_SECRET_KEY=sk_live_123
```

Le modèle reçoit :

```env
DATABASE_URL=⟦DATABASE_SECRET⟧
STRIPE_SECRET_KEY=⟦SECRET⟧
```

Le fichier réel n’est jamais modifié.

Un processus exécuté localement peut néanmoins utiliser les vraies valeurs.

Exemple :

```text
Agent demande :
npm test

Machine locale :
utilise le vrai DATABASE_URL

PrivacyCore :
inspecte stdout/stderr

LLM reçoit :
37 tests passed
```

Principe :

**Un processus local peut avoir besoin du secret sans que le LLM ait besoin de le connaître.**

---

# 12. Document Engine

Pipeline :

```text
File
 ↓
type detection
 ↓
native extraction possible?
 │
 ├── yes → extract
 │
 └── no → OCR
 ↓
structured representation
 ↓
PrivacyCore
```

Formats prioritaires :

### MVP

- TXT
- Markdown
- source code
- JSON
- YAML
- ENV
- CSV
- PDF avec texte

### V1

- DOCX
- images
- PDF scannés
- PDF mixtes texte/images

### Plus tard

- XLSX
- PPTX
- formats métier supplémentaires

---

# 13. PDF et OCR

PyMuPDF/PyMuPDF4LLM constitue la première solution envisagée pour le pipeline PDF.

Principe :

```text
PDF numérique
→ extraction directe

PDF mixte
→ extraction native + OCR sélectif

PDF scanné
→ OCR nécessaire
```

L’OCR complet de toutes les pages ne doit jamais être le comportement par défaut.

Les résultats doivent idéalement conserver :

- texte ;
- pages ;
- blocs ;
- bounding boxes ;
- structure.

Cela permettra ultérieurement de créer des versions visuellement pseudonymisées de documents.

---

# 14. Fast Path

Le produit doit être conçu autour du cas le plus fréquent :

**rien de sensible n’est détecté.**

Pipeline :

```text
request
   ↓
cheap inspection
   ↓
nothing sensitive
   ↓
PASS
```

Aucune extraction lourde ou OCR ne doit être exécuté sans raison.

Cache basé sur le hash du contenu :

```text
SHA-256(file)
      ↓
already scanned?
  yes       no
   │         │
 cached     analyse
 result
```

Une ressource inchangée ne doit pas être analysée intégralement à chaque lecture.

---

# 15. Points d’interception

Le produit doit progressivement couvrir :

### Lecture de fichiers

Contenu lu par l’agent.

### Tool calls

Arguments envoyés aux outils.

### Tool responses

Résultats renvoyés au modèle.

### Commandes shell

En particulier :

```text
cat
grep
head
tail
sed
python
scripts personnalisés
```

### stdout/stderr

Des secrets peuvent apparaître dans les logs même s’ils n’étaient pas présents dans le prompt.

### MCP

Résultats provenant de fichiers, bases ou services.

### Réponse LLM

Détection des tokens et restauration avant présentation ou écriture locale appropriée.

### Hors périmètre : entrée utilisateur

Le prompt saisi par l'utilisateur n'est ni inspecté, ni pseudonymisé, ni bloqué.

Ce que l'utilisateur écrit relève de sa responsabilité : il sait ce qu'il envoie.

Le produit protège uniquement les données que l'agent découvre de lui-même (fichiers, sorties de commandes, logs, résultats MCP), c'est-à-dire celles que l'utilisateur ne voit pas et ne contrôle pas.

---

# 16. Expérience d’installation

Objectif :

```text
Download
  ↓
Install
  ↓
Protected
```

Exemple :

```text
Scanning AI tools…

✓ Codex detected
✓ Claude Code detected

Installing protection…

✓ Codex protected
✓ Claude Code protected

You're protected.
```

Aucun fichier à créer manuellement.

Aucune modification par projet.

Aucune variable d’environnement à configurer à la main.

---

# 17. Application locale

Application légère dans la barre de menu.

Exemple :

```text
Privacy Guard
───────────────
● Protection active

Codex          Protected
Claude Code    Protected

This session
17 values protected
3 secrets blocked

[Settings]
```

Pas de dashboard complexe.

Le produit doit donner confiance sans demander une surveillance permanente.

---

# 18. Notifications

Notifications uniquement pour les événements importants.

Exemple :

```text
Privacy Guard blocked an API key
from being sent by Codex.
```

La pseudonymisation normale ne doit pas provoquer une notification à chaque occurrence.

---

# 19. Mode de restauration

Exemple :

```text
LLM output:

CV
⟦PERSON:91A7⟧
⟦EMAIL:F48C⟧
```

Avant écriture locale :

```text
PrivacyCore.restore()
```

Résultat :

```text
CV
Jean Dupont
jean@example.com
```

La restauration doit être effectuée uniquement sur une sortie destinée à un contexte local approprié.

---

# 20. Sécurité

## Aucune télémétrie sensible

Aucun contenu analysé ne doit être envoyé au développeur du produit.

## Logs locaux minimaux

Possible :

```text
email pseudonymized
api_key blocked
```

Interdit :

```text
jean@example.com pseudonymized
sk_live_xxxx blocked
```

## Telemetry

Désactivée par défaut.

Si l’utilisateur choisit de partager des métriques, elles doivent porter uniquement sur des informations techniques anonymes :

- OS ;
- version ;
- adapter utilisé ;
- erreurs ;
- latence.

Jamais sur le contenu inspecté.

---

# 21. Threat model

Le MVP protège principalement contre l’envoi accidentel de données sensibles au fournisseur du modèle.

Il ne prétend pas initialement protéger contre :

- malware disposant d’un accès complet à la machine ;
- utilisateur root hostile ;
- compromission du système d’exploitation ;
- applications externes ne passant pas par un adapter supporté ;
- exfiltration volontaire via des canaux totalement extérieurs au workflow protégé ;
- données saisies volontairement par l'utilisateur dans son prompt (voir §15, hors périmètre).

La promesse commerciale ne doit donc jamais être :

> « Aucune donnée ne pourra jamais fuiter. »

Ni :

> « Tout ce que vous envoyez à l’IA est protégé. »

(le prompt de l’utilisateur n’est pas couvert).

Mais :

> « When Claude Code or Codex reads your files or command output, the personal data and secrets we detect are replaced before they reach the model. »

> « Quand Claude Code ou Codex lit vos fichiers ou le résultat d’une commande, les données personnelles et les secrets détectés sont remplacés avant d’arriver au modèle. »

Chaque partie de cette phrase est tenable :

- **« Claude Code or Codex »** : on nomme uniquement les agents dont l’adapter est testé. Jamais « all AI agents ».
- **« reads your files or command output »** : le périmètre est ce que l’agent récupère via ses outils (fichiers, shell, MCP). Ni le prompt de l’utilisateur, ni les outils exécutés côté fournisseur (recherche web, par exemple).
- **« we detect »** : la détection n’est pas parfaite (voir §23). On ne promet pas 100 %.
- **« replaced before they reach the model »** : le remplacement a lieu sur la machine, avant l’envoi. Les vraies valeurs ne sont restaurées qu’en local.

Pour Codex, la promesse ne doit être communiquée qu’après validation par le prototype : son hook `PostToolUse` ne propose pas encore de champ officiel pour réécrire le résultat d’un outil.

---

# 22. Performance

Objectif principal :

l’utilisateur ne doit pas avoir envie de désactiver le produit pour gagner en vitesse.

Objectifs MVP à mesurer :

- fast path texte : p95 < 50 ms de surcharge ;
- zéro OCR pour un PDF disposant d’un texte exploitable ;
- cache systématique des fichiers déjà inspectés ;
- chargement différé des modèles NLP lourds ;
- consommation mémoire limitée lorsqu’aucun traitement n’est en cours.

Les chiffres définitifs seront établis par benchmark avant GA.

---

# 23. Qualité de détection

Le produit ne doit jamais prétendre détecter 100 % des données personnelles.

Un benchmark interne doit contenir :

- code ;
- `.env` ;
- logs ;
- CV ;
- contrats ;
- factures ;
- documents français et anglais ;
- PDF natifs ;
- scans ;
- faux positifs courants.

Mesures :

- recall ;
- precision ;
- faux positifs ;
- faux négatifs ;
- latence ;
- mémoire.

Les secrets à format déterministe doivent atteindre un niveau de fiabilité supérieur aux entités sémantiques comme les noms ou les adresses.

---

# 24. MVP

## Plateforme

macOS uniquement.

## Agents

- Codex
- Claude Code

## Données

### Pseudonymisation

- personnes ;
- emails ;
- téléphones ;
- adresses.

### Blocage

- API keys ;
- private keys ;
- credentials de bases de données ;
- JWT ;
- cartes bancaires.

### Documents

- code ;
- texte ;
- Markdown ;
- ENV ;
- JSON/YAML ;
- PDF numérique.

### Fonctionnalités

- installation unique ;
- détection des agents ;
- activation globale ;
- PrivacyCore ;
- vault local ;
- fast path ;
- cache ;
- pseudonymisation ;
- restauration ;
- interface menu bar ;
- journal local sans contenu sensible.

---

# 25. V1

Ajouter :

- PDF scannés ;
- OCR sélectif ;
- images ;
- DOCX ;
- davantage de catégories PII ;
- règles personnalisables ;
- tests automatiques de fuite ;
- mise à jour automatique des adapters.

---

# 26. V2+

Candidats :

- Windows ;
- Linux ;
- Gemini CLI ;
- Cursor ;
- autres agents ;
- XLSX ;
- PPTX ;
- règles par workspace ;
- détection automatique d’un nouvel agent installé ;
- SDK pour adapters communautaires ;
- adapters communautaires ;
- UI avancée pour politiques.

---

# 27. Non-objectifs

Le produit n’a pas vocation à devenir :

- proxy LLM cloud généraliste ;
- outil de routing entre modèles ;
- plateforme d’observabilité ;
- dashboard financier LLM ;
- système IAM ;
- solution SOC ;
- gestionnaire de secrets ;
- produit de compliance enterprise complet.

Cette limitation de scope constitue une partie de son positionnement.

---

# 28. Business model recommandé

## Architecture open-core

### Open source

`PrivacyCore`

Inclure :

- détection ;
- tokenisation ;
- restauration ;
- format des policies ;
- SDK d’adapters ;
- tests de sécurité ;
- certains adapters.

Pourquoi :

Le produit demande à l’utilisateur de lui faire confiance avec les données les plus sensibles de sa machine.

Permettre :

```text
git clone
read code
build locally
```

constitue donc un avantage commercial plutôt qu’un problème.

Cela permet aussi à la communauté de créer :

- détecteurs ;
- formats ;
- langues ;
- adapters pour de nouveaux agents.

### Produit commercial

`Privacy Guard Desktop`

Comprend :

- application macOS signée ;
- installation en un clic ;
- détection automatique des agents ;
- configuration automatique ;
- mises à jour ;
- menu bar ;
- gestion du vault ;
- diagnostics ;
- adapters maintenus/testés ;
- désinstallation propre.

C’est principalement cela que l’utilisateur paie.

---

# 29. Pricing envisagé

### Community

Gratuit.

PrivacyCore + CLI.

Destiné aux personnes souhaitant tout configurer elles-mêmes.

### Desktop

Prix de lancement envisagé :

**14,99 € – 24,99 € une fois.**

Inclut :

- version majeure actuelle ;
- correctifs de bugs ;
- correctifs de sécurité ;
- mises à jour des adapters nécessaires au fonctionnement de cette version.

Pas d’abonnement.

### Upgrade majeur

Exemple :

```text
Privacy Guard 1.x
→ acheté une fois
→ continue de fonctionner

Privacy Guard 2
→ nouvelles fonctionnalités importantes
→ upgrade facultatif
```

L’utilisateur n’est jamais obligé de repayer simplement pour continuer à utiliser la version achetée.

---

# 30. Stratégie open source

Approche recommandée :

```text
PrivacyCore          OPEN SOURCE
Adapter SDK          OPEN SOURCE
Detection rules      OPEN SOURCE
Community adapters   OPEN SOURCE

Desktop UX           COMMERCIAL
Auto-configuration   COMMERCIAL
Signed binaries      COMMERCIAL
Updater              COMMERCIAL
Premium adapters     éventuellement COMMERCIAL
```

Une licence comme MPL-2.0 pourrait être étudiée pour le cœur : elle permet une utilisation commerciale tout en demandant que les modifications apportées aux fichiers couverts restent disponibles sous la même licence.

Le choix définitif de licence devra être validé séparément avant publication.

---

# 31. Pourquoi ne pas tout fermer

Pour un produit déclarant :

> « Faites-nous confiance, notre logiciel empêche vos secrets de quitter votre ordinateur »

une boîte noire peut devenir un frein.

Open-sourcer le moteur permet à un développeur de vérifier :

- qu’aucune donnée n’est envoyée ailleurs ;
- comment fonctionne le vault ;
- comment les secrets sont détectés ;
- ce qui se passe avant l’appel au modèle.

La transparence devient une fonctionnalité du produit.

---

# 32. Pourquoi ne pas tout rendre gratuit

L’open source répond à :

> « Puis-je lui faire confiance ? »

Le produit payant répond à :

> « Puis-je l’installer en trente secondes et ne plus jamais m’en occuper ? »

Le produit commercial vend principalement la simplicité, la maintenance et la fiabilité.

---

# 33. Positionnement

Ne pas communiquer comme :

> « DLP for AI agents »

Trop enterprise.

Ne pas communiquer principalement comme :

> « NER-powered PII anonymization framework »

Trop technique.

Ne pas communiquer non plus comme :

> « Keep personal data and secrets out of Codex and Claude Code. »

Trop large : laisse entendre que tout est protégé, y compris le prompt de l’utilisateur (hors périmètre, voir §15).

Positionnement utilisateur :

**Your AI agent reads your files. It doesn't need your private data.**

Puis :

**Install once. Detection and vault stay on your machine.**

Les slogans doivent rester cohérents avec la promesse du §21 : on parle de ce que l’agent lit, jamais de « tout ce qui est envoyé à l’IA ». On évite aussi « Everything stays local » : le contenu non sensible part bien vers le modèle, seuls la détection et le vault restent sur la machine.

---

# 34. Différenciation principale

Le moat produit n’est pas le modèle NLP.

Il est constitué de :

1. installation en un clic ;
2. interception systématique ;
3. excellente intégration aux agents ;
4. très faible latence ;
5. couverture de multiples chemins d’accès ;
6. restauration transparente ;
7. traitement local ;
8. architecture auditée/open source ;
9. fonctionnement sans configuration projet ;
10. communauté capable d’ajouter rapidement de nouveaux adapters.

---

# 35. Critères de réussite du MVP

Le MVP est considéré réussi lorsqu’un utilisateur peut :

1. installer l’application ;
2. voir Codex et Claude Code détectés automatiquement ;
3. lancer Codex normalement ;
4. demander l’analyse d’un CV contenant de vraies PII ;
5. vérifier que le modèle reçoit uniquement les pseudonymes ;
6. recevoir un document final restauré ;
7. demander à l’agent de lire un `.env` ;
8. constater que les secrets sont bloqués ;
9. utiliser un projet normal sans percevoir de ralentissement significatif ;
10. reproduire le comportement sans configuration supplémentaire dans un second projet.

---

# 36. North Star

L’expérience cible est :

```text
Utilisateur installe Privacy Guard.

Il oublie qu'il existe.

Quelques semaines plus tard :

"Privacy Guard has prevented
427 sensitive values from being sent
to AI models."

Et tout a continué de fonctionner normalement.
```

C’est cette invisibilité qui constitue le produit.
