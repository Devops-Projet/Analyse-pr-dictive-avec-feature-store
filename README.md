# Plateforme de feature store pour l'analyse prédictive bancaire

Magasin centralisé de variables de machine learning, partagé par plusieurs modèles
(scoring crédit et propension marketing), pour éviter de les recalculer dans chaque projet.

**Outils :** Git/GitHub, DVC, MLflow, Docker, FastAPI, PostgreSQL, pandas, scikit-learn.

## État du projet

En cours de construction : le cadrage, les conteneurs, la génération des données et le
feature store et son API de récupération sont en place. Les modèles et les routes de
prédiction restent à réaliser.

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

## Pipeline

`dvc repro` enchaîne `generate → validate → build_features → load_features`. La dernière étape
charge les variables dans PostgreSQL et est relancée à chaque exécution, car DVC ne suit pas le
contenu de la base.

## Données

Le pipeline écrit dans `data/`, qui est ignoré par Git. Aucun remote DVC n'est configuré pour
l'instant : les données synthétiques sont régénérées à l'identique par `dvc repro`, grâce à
la seed de `params.yaml`.

## Documentation

- [Cadrage](docs/cadrage.md)
- [Variables partagées](docs/variables.md)
- [Catalogue des variables](docs/feature_catalog.md)
- [Conventions de contribution](CONTRIBUTING.md)
