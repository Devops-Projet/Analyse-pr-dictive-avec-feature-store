.PHONY: all setup up down pipeline test lint lock models rollback

export UID := $(shell id -u)
export GID := $(shell id -g)

all: up pipeline

# Crée .env à partir du modèle s'il n'existe pas encore
setup:
	test -f .env || cp .env.example .env

up: setup
	docker compose up -d --build --wait

down:
	docker compose down

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

test: setup
	docker compose up -d --wait postgres
	docker compose run --rm --no-deps --build pipeline python -m pytest

lint: setup
	docker compose run --rm --no-deps pipeline sh -c \
		"ruff check . && black --check ."

# Régénère requirements.lock dans le même Python que les images
lock:
	docker run --rm -u $(UID):$(GID) -e HOME=/tmp -v "$(CURDIR)":/src -w /src python:3.12-slim sh -c \
		"python -m pip install --quiet --user pip-tools && python -m piptools compile --quiet --strip-extras --extra dev --output-file requirements.lock pyproject.toml"
