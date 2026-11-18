# Modèles consommateurs

Deux modèles lisent leurs variables **uniquement dans le feature store** : aucune variable
n'est recalculée dans leur code. Ils partagent 9 variables (âge, ancienneté, revenu, soldes
moyens, transactions et montants sur 30 jours).

| | Scoring crédit | Propension marketing |
|---|---|---|
| Nom dans le registre MLflow | `credit_scoring` | `marketing_propensity` |
| Cible | `defaut` (14 % de positifs) | `souscription` (29 % de positifs) |
| Variables | 15 | 13 |
| Modèle | Régression logistique pondérée | Régression logistique pondérée |
| Seuil minimal de mise en production | AUC 0,65 | AUC 0,60 |

## Données d'entraînement

- **Variables :** jointure au point dans le temps à la date d'étiquetage
  (`models.label_date` dans `params.yaml`) : chaque client reçoit le dernier instantané calculé
  à cette date ou avant.
- **Cibles :** lues dans `data/raw/clients.csv`, séparément des variables.
- **Découpage :** 75 % entraînement, 25 % test, stratifié et fixé par la seed. Le même découpage
  sert à l'entraînement et à l'évaluation, pour comparer les versions sur les mêmes clients.

## Modèles essayés

Validation croisée stratifiée à 5 plis sur les 2 000 clients (AUC moyenne ± écart-type) :

| Modèle | Scoring | Marketing |
|---|---|---|
| Régression logistique, C = 0,5 | 0,706 ± 0,049 | 0,653 ± 0,027 |
| **Régression logistique, C = 0,05** | **0,708 ± 0,049** | **0,655 ± 0,026** |
| Gradient boosting, 200 arbres, profondeur 3 | 0,639 ± 0,058 | 0,617 ± 0,028 |
| Gradient boosting, 100 arbres, profondeur 2 | 0,690 ± 0,052 | 0,639 ± 0,031 |

La régression logistique l'emporte sur les deux cibles : avec 2 000 clients, le gradient
boosting sur-apprend. Elle a aussi l'avantage d'être interprétable et de se sérialiser au
format `skops` sans type à risque.

## Résultats sur le jeu de test (version 1)

| Métrique | Scoring | Marketing |
|---|---|---|
| AUC | 0,735 | 0,646 |
| F1 | 0,361 | 0,504 |
| Précision | 0,253 | 0,411 |
| Rappel | 0,629 | 0,653 |

Le seuil de décision est 0,5. Avec la pondération des classes, le modèle de scoring privilégie
le rappel : il repère 63 % des défauts, au prix de nombreuses fausses alertes.

## Plafond théorique

Le générateur tire chaque cible à partir d'un facteur caché par client (`risque` pour le
défaut, `appetence` pour la souscription), avec une part de hasard
(`pipelines/generate_data.py`). Même un modèle qui connaîtrait ce facteur ne classerait pas
parfaitement les clients. Son AUC, estimée par simulation sur 2 millions de tirages, donne la
limite atteignable :

| Modèle | AUC en test | Plafond théorique | Part du plafond |
|---|---|---|---|
| Scoring crédit | 0,735 | 0,782 | 94 % |
| Propension marketing | 0,646 | 0,790 | 82 % |

Le scoring est proche de la limite. Pour le marketing, l'écart vient des variables : le
facteur `appetence` n'est observé qu'à travers des signaux faibles (usage de l'application,
nombre de produits, contacts). Le gagner suppose de nouvelles variables dans le store, pas un
autre réglage du modèle. Avec 500 clients en test, l'écart-type de l'AUC mesurée est d'environ 0,02 à 0,03.

## Suivi MLflow

Chaque entraînement enregistre dans MLflow (http://localhost:5000) :

- les hyperparamètres, la seed, la taille des jeux et la **version du feature set** ;
- les métriques de test (`auc`, `f1`, `precision`, `recall`) et l'AUC d'entraînement ;
- la liste des variables (`features.json`) et le modèle, avec sa signature ;
- une nouvelle version dans le registre de modèles.

## Règle de mise en production

L'étape DVC `evaluate` compare la version candidate à la version en production **sur le même
jeu de test**. La candidate est promue si :

1. son AUC atteint le seuil minimal ;
2. et son AUC est strictement supérieure à celle de la version en production, s'il y en a une.

La version promue reçoit l'alias `production` ; l'ancienne reçoit l'alias `previous`. La
décision est enregistrée en tag sur la version et dans `reports/<modèle>.json`.

Si aucun modèle n'a de version en production à la fin du pipeline, l'étape échoue.

## Commandes

```bash
make models                          # alias production / previous de chaque modèle
make rollback MODEL=credit_scoring   # remet la version précédente en production
```

## Limites

- Données synthétiques : les performances ne préjugent pas d'un cas réel.
- Les attributs `revenu_mensuel`, `nb_produits_detenus` et `utilise_app_mobile` sont des valeurs
  actuelles, sans historique.
- Le seuil de décision n'est pas optimisé selon un coût métier.
