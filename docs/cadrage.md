# Cadrage

## Besoin

La banque veut centraliser ses variables de machine learning dans un magasin unique,
afin qu'elles servent à plusieurs usages sans être recalculées dans chaque projet.

## Usages métier

| Usage | Question posée | Cible | Statut |
|---|---|---|---|
| Scoring crédit | Le client risque-t-il de faire défaut ? | `defaut` (0/1) | Obligatoire |
| Propension marketing | Le client va-t-il souscrire à l'offre ? | `souscription` (0/1) | Obligatoire |
| Risque ou attrition | Le client risque-t-il de partir ? | `attrition` (0/1) | Optionnel |

## Périmètre

**Inclus :** données tabulaires, base PostgreSQL de variables, API de récupération et de
prédiction, deux modèles consommateurs, versionnage DVC, suivi MLflow, CI et supervision.

**Exclus :** store en ligne à faible latence (Redis), orchestration (Airflow), Feast.
Ces pistes seront traitées comme améliorations possibles dans le bilan.

## Données

Les données viennent d'un générateur synthétique à seed fixe (clients, comptes,
transactions). Elles ne contiennent aucune donnée personnelle réelle et ne sont soumises
à aucune contrainte de licence.

## Contraintes

- Une seule commande documentée reconstruit l'environnement et relance le pipeline.
- Les modèles lisent leurs variables uniquement depuis le store.
- Le remote DVC doit être accessible depuis une autre machine.
