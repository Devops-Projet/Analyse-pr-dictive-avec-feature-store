# Plateforme de feature store pour l'analyse prédictive bancaire

Magasin centralisé de variables de machine learning, partagé par plusieurs modèles
(scoring crédit et propension marketing), pour éviter de les recalculer dans chaque projet.

**Outils :** Git/GitHub, DVC, MLflow, Docker, FastAPI, PostgreSQL, pandas, scikit-learn.

## État du projet

En cours de construction : le cadrage, les conteneurs et la génération des données sont en
place. Le feature store, les modèles et les routes métier de l'API restent à réaliser.

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

## Données

Le pipeline écrit dans `data/`, qui est ignoré par Git. Aucun remote DVC n'est configuré pour
l'instant : les données synthétiques sont régénérées à l'identique par `dvc repro`, grâce à
la seed de `params.yaml`.

## Documentation

- [Cadrage](docs/cadrage.md)
- [Variables partagées](docs/variables.md)
- [Conventions de contribution](CONTRIBUTING.md)
