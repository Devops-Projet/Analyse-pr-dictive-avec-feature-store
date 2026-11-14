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
