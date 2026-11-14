# Plateforme de feature store pour l'analyse prédictive bancaire

[![CI](https://github.com/Devops-Projet/Analyse-pr-dictive-avec-feature-store/actions/workflows/ci.yml/badge.svg)](https://github.com/Devops-Projet/Analyse-pr-dictive-avec-feature-store/actions/workflows/ci.yml)

Magasin centralisé de variables de machine learning, partagé par plusieurs modèles
(scoring crédit et propension marketing), pour éviter de les recalculer dans chaque projet.

**Outils :** Git/GitHub, DVC, MLflow, Docker, FastAPI, PostgreSQL, pandas, scikit-learn.

## État du projet

En cours de construction : les données, le feature store, son API de récupération et les deux
modèles consommateurs, leurs routes de prédiction et la CI sont en place. La supervision reste
à réaliser.

## Démarrage

Prérequis : Docker avec Docker Compose, et `make`.

```bash
make all
```

Cette commande crée `.env` à partir de `.env.example`, démarre les services, attend qu'ils
soient prêts, puis lance le pipeline avec `dvc repro`.

| Commande | Rôle |
|---|---|
| `make up` / `make down` | Démarrer ou arrêter les services |
| `make pipeline` | Relancer le pipeline DVC |
| `make test` / `make lint` | Lancer les tests ou le lint |
| `make audit` | Rechercher un secret dans les fichiers suivis par Git |
| `make smoke` | Contrôler le service démarré |
| `make lock` | Régénérer `requirements.lock` |

| Service | Adresse |
|---|---|
| API | http://localhost:8000/health |
| MLflow | http://localhost:5000 |

## API de récupération

Documentation interactive : http://localhost:8000/docs

| Route | Rôle |
|---|---|
| `GET /features/{client_id}` | Dernières variables d'un client |
| `POST /features/batch` | Variables de 1 à 1 000 clients |
| `GET /features/definitions` | Catalogue des variables |
| `GET /features/versions` | Versions chargées du store |
| `GET /health` | État du service |

Paramètres optionnels : `version` (la plus récente par défaut), `as_of` (lecture au point dans
le temps) et `features` (sous-ensemble de variables).

```bash
curl "http://localhost:8000/features/42?features=age&features=revenu_mensuel"
# {"client_id":42,"event_timestamp":"2026-01-01T00:00:00",
#  "features":{"age":64.0,"revenu_mensuel":2412.88},"version":"v-6df062c911ba"}

curl -X POST http://localhost:8000/features/batch \
  -H "content-type: application/json" -d '{"client_ids": [1, 5000], "features": ["age"]}'
# {"version":"v-6df062c911ba",
#  "results":[{"client_id":1,"event_timestamp":"2026-01-01T00:00:00","features":{"age":26.0}}],
#  "missing":[5000]}
```

Codes d'erreur : `404` pour un client ou une version inconnus, `400` pour une variable
inconnue, `422` pour une requête invalide.

## Prédiction

| Route | Rôle |
|---|---|
| `POST /predict/scoring` | Probabilité de défaut d'un client |
| `POST /predict/marketing` | Probabilité de souscription d'un client |

L'API lit les variables du client dans la version du store sur laquelle le modèle a été
entraîné, puis applique le modèle en production du registre MLflow.

```bash
curl -X POST http://localhost:8000/predict/scoring \
  -H "content-type: application/json" -d '{"client_id": 42}'
# {"client_id":42,"model":"credit_scoring","model_version":"1",
#  "feature_set_version":"v-6df062c911ba","event_timestamp":"2026-01-01T00:00:00",
#  "probability":0.5537,"prediction":1}
```

Codes d'erreur : `404` pour un client inconnu, `503` si aucun modèle n'est en production.

Après chaque déploiement, `make smoke` vérifie le parcours réel. Le retour arrière et la
conduite à tenir en cas d'incident sont décrits dans [docs/runbook.md](docs/runbook.md).

## Pipeline

`dvc repro` enchaîne `generate → validate → build_features → load_features → train_scoring →
train_marketing → evaluate`. `load_features` charge les variables dans PostgreSQL et est
relancée à chaque exécution, car DVC ne suit pas le contenu de la base. Si le registre MLflow a
été vidé, `make pipeline` réentraîne les modèles automatiquement.

## Modèles

Deux modèles lisent leurs variables dans le store et sont suivis dans MLflow
(http://localhost:5000) : `credit_scoring` et `marketing_propensity`. Un modèle n'est mis en
production que si son AUC dépasse un seuil minimal et celle de la version en production.

| Commande | Rôle |
|---|---|
| `make models` | Versions en production et précédentes |
| `make rollback MODEL=credit_scoring` | Remettre la version précédente en production |

Voir [docs/modeles.md](docs/modeles.md) pour les modèles essayés et les résultats.

## Intégration continue

GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) s'exécute à chaque
pull request et à chaque push sur `main` :

1. **Lint et secrets :** ruff, black et detect-secrets ;
2. **Tests :** tests unitaires et d'intégration sur un PostgreSQL de service, avec couverture ;
3. **Validation des modèles :** seuil d'AUC, probabilités entre 0 et 1, valeurs manquantes ;
4. **Build :** images de l'API et du pipeline, étiquetées avec le hash du commit.

Un contrôle en échec bloque les étapes suivantes. En local, les images portent aussi le hash du
commit (`IMAGE_TAG`), ce qui permet d'identifier la version déployée.

## Données

Le pipeline écrit dans `data/`, qui est ignoré par Git. Aucun remote DVC n'est configuré pour
l'instant : les données synthétiques sont régénérées à l'identique par `dvc repro`, grâce à
la seed de `params.yaml`.

## Documentation

- [Cadrage](docs/cadrage.md)
- [User stories et définition de « terminé »](docs/user_stories.md)
- [Variables partagées](docs/variables.md)
- [Catalogue des variables](docs/feature_catalog.md)
- [Modèles](docs/modeles.md)
- [Procédures d'exploitation](docs/runbook.md)
- [Conventions de contribution](CONTRIBUTING.md)
