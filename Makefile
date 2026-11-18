.PHONY: all setup up down pipeline test lint audit lock models rollback smoke monitoring dora data-pull data-push

export UID := $(shell id -u)
export GID := $(shell id -g)
# Les images portent le hash du commit : chaque version déployée est identifiable.
export IMAGE_TAG ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)

all: up pipeline

# Crée .env à partir du modèle, puis y ajoute les variables apparues depuis dans .env.example
setup:
	@test -f .env || cp .env.example .env
	@python3 scripts/sync_env.py

up: setup
	docker compose up -d --build --wait

down:
	docker compose --profile monitoring down

# Si le registre MLflow a été vidé (docker compose down -v), DVC considère les modèles comme
# à jour : on force alors leur réentraînement pour que l'API ait toujours un modèle à servir.
pipeline: setup
	docker compose run --rm --build pipeline sh -c "dvc repro && \
		(python -m models.common.registry check || \
		dvc repro --force --single-item train_scoring train_marketing evaluate)"

# État des alias production / previous de chaque modèle
models: setup
	docker compose run --rm pipeline sh -c "python -m models.common.registry status credit_scoring \
		&& python -m models.common.registry status marketing_propensity"

# Retour à la version précédente : make rollback MODEL=credit_scoring
rollback: setup
	docker compose run --rm pipeline python -m models.common.registry rollback $(MODEL)

# Prometheus (http://localhost:9090) et Grafana (http://localhost:3000)
monitoring: setup
	docker compose --profile monitoring up -d --build --wait

# Contrôle après déploiement sur le service démarré (voir docs/runbook.md)
smoke: setup
	docker compose run --rm --no-deps -e API_URL=http://api:8000 pipeline python scripts/smoke_test.py

test: setup
	docker compose up -d --wait postgres
	docker compose run --rm --no-deps --build pipeline python -m pytest

lint: setup
	docker compose run --rm --no-deps pipeline sh -c \
		"ruff check . && black --check ."

# Échoue si un mot de passe ou une clé est détecté dans les fichiers suivis par Git
audit: setup
	docker compose run --rm --no-deps pipeline python scripts/check_secrets.py  # pragma: allowlist secret

# Données versionnées sur le remote DVC (DagsHub). Lecture et envoi demandent un jeton
# DagsHub dans .dvc/config.local (voir README, section Données).
data-pull: setup
	docker compose run --rm --no-deps pipeline dvc pull

data-push: setup
	docker compose run --rm --no-deps pipeline dvc push

# Indicateurs DORA mesurés sur l'historique de main (voir docs/dora.md)
dora:
	git fetch -q origin main && python3 scripts/dora.py origin/main

# Régénère requirements.lock dans le même Python que les images
lock:
	docker run --rm -u $(UID):$(GID) -e HOME=/tmp -v "$(CURDIR)":/src -w /src python:3.12-slim sh -c \
		"python -m pip install --quiet --user pip-tools && python -m piptools compile --quiet --strip-extras --extra dev --output-file requirements.lock pyproject.toml"
