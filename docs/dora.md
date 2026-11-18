# Indicateurs DORA

Les quatre indicateurs DORA mesurent la performance de livraison : deux pour la vitesse
(fréquence, délai) et deux pour la stabilité (taux d'échec, temps de rétablissement).

**Définition retenue d'une livraison :** une fusion de pull request dans `main`. Chaque fusion
déclenche la CI, qui construit les images étiquetées avec le hash du commit ; `make all`
les déploie.

## Mesures au 18/11/2026

| Indicateur | Valeur | Source |
|---|---|---|
| Fréquence de livraison | 6 fusions dans `main` sur 2 semaines actives, soit 3 par semaine | `python3 scripts/dora.py` |
| Délai de mise en production | Médiane 1,9 h entre un commit et sa fusion (54 commits) ; maximum 211 h | `python3 scripts/dora.py` |
| Taux d'échec des changements | 1 livraison à corriger sur 7 tentatives, soit environ 14 % | Journal des incidents ci-dessous |
| Temps de rétablissement | 7 min entre la dernière fusion fautive et la fusion corrective | Journal des incidents ci-dessous |

Les 7 tentatives de livraison sont les PR #1 à #5, le lot des PR #6 à #9 et la PR #10.
Le délai maximum de 211 h correspond aux premiers commits du socle (30/10), fusionnés le 08/11
après la mise en place de Docker et du pipeline de données : ils attendaient d'être utilisables
ensemble.

## Lecture

| Indicateur | Niveau atteint (repères DORA) |
|---|---|
| Fréquence | Élevé : entre une fois par jour et une fois par semaine |
| Délai | Élite en médiane (moins d'un jour), mais irrégulier |
| Taux d'échec | Élite à élevé (repère élite : 0 à 15 %) |
| Rétablissement | Élite (moins d'une heure) |

Ces valeurs portent sur un petit nombre de livraisons, faites par deux personnes sur quelques
semaines : elles décrivent le fonctionnement du projet, pas un niveau stable dans le temps. La
CI n'existe que depuis la PR #8 ; les premières livraisons n'avaient pas de contrôle
automatique.

## Journal des incidents

### 14/11/2026 · Étapes G à K absentes de `main`

| | |
|---|---|
| **Symptôme** | Après la fusion des PR #5 à #9, `main` ne contenait que la PR #5 |
| **Cause** | Les PR #6 à #9 étaient empilées : la base de chacune était la branche de la précédente. Fusionnées depuis l'interface GitHub sans changer la base, elles sont arrivées dans les branches intermédiaires |
| **Détection** | Vérification de `main` après fusion (`git log`, comparaison des branches), 14/11 vers 19:58 |
| **Impact** | Aucun service touché : le code de `main` restait fonctionnel, mais les modèles, la prédiction, la CI et la supervision n'étaient pas livrés |
| **Rétablissement** | PR #10 (`feature/ci` → `main`, contenu identique à la dernière branche), CI réussie, fusion à 20:03:59 ; clone neuf, `make all` et `make smoke` réussis |
| **Durée** | 19:57:31 (dernière fusion fautive) → 20:03:59 (fusion corrective) : environ 7 min |
| **Action d'amélioration** | Toute pull request part directement de `main` ; protection de `main` avec relecture obligatoire. Responsable : hichamouaouche |

Les problèmes trouvés avant livraison, par les tests ou la vérification sur machine propre, ne
sont pas comptés comme des échecs de changement : ils sont listés dans les incidents connus du
[runbook](runbook.md#incidents-connus).

## Mettre à jour les mesures

```bash
git fetch && python3 scripts/dora.py origin/main
```

Après chaque incident, ajouter une entrée au journal avec la même structure, puis recalculer le
taux d'échec et le temps de rétablissement.
