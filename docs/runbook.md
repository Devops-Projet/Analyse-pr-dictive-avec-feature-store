# Procédures d'exploitation

## Responsabilités

| Rôle | Personne | Intervient sur |
|---|---|---|
| Responsable de la livraison et des modèles | hichamouaouche | Pipeline, registre MLflow, retour arrière |
| Responsable de l'API et de la supervision | Abdessamad-PRO | Conteneurs, API, métriques, alertes |

Chacun relit les changements de l'autre avant leur fusion (voir la
[définition de « terminé »](user_stories.md#définition-de--terminé-)).

## Livrer une nouvelle version

1. La pull request est approuvée et la CI réussit.
2. Fusion dans `main`, puis sur la machine cible : `git pull && make all`.
3. Contrôle après déploiement : `make smoke`.
4. Si un contrôle échoue : **arrêter la livraison** et appliquer le retour arrière ci-dessous.

`make smoke` vérifie le service réel : santé, lecture des variables d'un client, refus d'un
client inconnu et prédiction des deux modèles.

## Signaux qui imposent un arrêt

- `make smoke` échoue ;
- l'étape `evaluate` refuse une version (AUC sous le seuil ou non meilleure que la production) ;
- la part de réponses en erreur 5xx de l'API dépasse le seuil d'alerte (voir la supervision).

## Supervision

`make monitoring` démarre Prometheus (http://localhost:9090) et Grafana
(http://localhost:3000, compte `admin`, mot de passe `GRAFANA_ADMIN_PASSWORD` de `.env`).

| Signal | Où le lire |
|---|---|
| Disponibilité du store et des modèles | `GET /ready`, métrique `service_ready` |
| Trafic, erreurs et latence par route | `GET /metrics`, tableau de bord Grafana |
| Prédictions par modèle, version et classe | métrique `predictions_total` |
| Fraîcheur des variables | `feature_store_last_load_age_seconds`, `/ready` |
| Dérive des variables | `reports/drift.json` (étape DVC `drift`) |

### Alertes

| Alerte | Condition | Responsable | Action |
|---|---|---|---|
| `APIInjoignable` | Collecte en échec depuis 1 min | Abdessamad-PRO | `docker compose ps`, `docker compose logs api` |
| `ServiceNonPret` | `service_ready == 0` depuis 2 min | hichamouaouche | `GET /ready` pour le détail, puis `make pipeline` |
| `TauxErreursEleve` | Plus de 5 % de réponses 5xx sur 5 min | Abdessamad-PRO | Arrêter la livraison, retour arrière si elle est récente |
| `LatencePredictionElevee` | p95 des prédictions > 0,5 s sur 5 min | Abdessamad-PRO | Vérifier MLflow et PostgreSQL |
| `VariablesPerimees` | Store non rechargé depuis 7 jours | hichamouaouche | `make pipeline` |

Les alertes sont visibles dans Prometheus (onglet *Alerts*). Aucun envoi de notification
(e-mail, messagerie) n'est configuré : c'est une limite connue du projet.

### Dérive des variables

L'étape `drift` compare l'instantané de référence et l'instantané courant (`params.yaml`,
section `monitoring`) avec le PSI et le test de Kolmogorov-Smirnov :

- **stable :** PSI ≤ 0,1 et p-valeur KS ≥ 0,01 ;
- **avertissement :** PSI entre 0,1 et 0,25, ou p-valeur KS < 0,01 ;
- **alerte :** PSI > 0,25 → examiner la variable et envisager un réentraînement.

Sur les données actuelles, trois variables sont en avertissement (`nb_retards_paiement_12m`,
`jours_retard_max_12m`, `solde_min_90j`). C'est un effet du jeu synthétique : l'historique
commence 365 jours avant le 01/01/2026, donc la fenêtre de 12 mois de l'instantané du
01/10/2025 est incomplète. Aucun PSI ne dépasse 0,06.

## Retour arrière d'un modèle

Quand une version mise en production se dégrade :

```bash
make models                          # repérer les versions production et previous
make rollback MODEL=credit_scoring   # ou MODEL=marketing_propensity
make smoke                           # vérifier le service rétabli
```

L'API résout l'alias `production` à chaque requête : la version rétablie est servie
immédiatement, sans redémarrage. La version retirée reçoit le tag `retiree_le` dans MLflow.

Un seul retour arrière est possible à la fois : il n'existe plus de version `previous` ensuite.
Pour revenir plus loin, réaffecter l'alias `production` à la version voulue dans l'interface
MLflow (Models → modèle → version → Aliases).

## Retour arrière du code ou des données

- **Code :** revenir au commit précédent de `main` (`git revert`), puis `make all`.
- **Variables du store :** chaque version reste disponible dans PostgreSQL ; un modèle lit
  toujours la version du store sur laquelle il a été entraîné.
- Un retour de version du code ne restaure pas les données : les versions du store ne sont
  jamais supprimées automatiquement.

## Incidents connus

| Symptôme | Cause probable | Action |
|---|---|---|
| Le pipeline s'arrête sur « Variables d'environnement manquantes » | `.env` incomplet | Compléter `.env` à partir de `.env.example` |
| `503` « Aucune version … en production » | Registre MLflow vidé | `make pipeline` (réentraînement automatique) |
| `503` « Version du store du modèle absente » | Base PostgreSQL vidée | `make pipeline` |
| `make smoke` : service injoignable | API arrêtée ou en échec | `docker compose ps`, puis `docker compose logs api` |

## Après un incident

Noter les faits (heure, symptôme, utilisateurs touchés, actions), puis choisir **une action
d'amélioration** avec un responsable et une date de suivi : par exemple un test ou un contrôle
qui aurait détecté le problème plus tôt. L'analyse porte sur les conditions de l'incident, pas
sur la recherche d'un coupable.
