.PHONY: all setup up down pipeline test lint lock

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

pipeline: setup
	docker compose run --rm --build pipeline

test: setup
	docker compose run --rm --no-deps --build pipeline python -m pytest

lint: setup
	docker compose run --rm --no-deps pipeline sh -c \
		"ruff check . && black --check ."

# Régénère requirements.lock dans le même Python que les images
lock:
	docker run --rm -u $(UID):$(GID) -e HOME=/tmp -v "$(CURDIR)":/src -w /src python:3.12-slim sh -c \
		"python -m pip install --quiet --user pip-tools && python -m piptools compile --quiet --strip-extras --extra dev --output-file requirements.lock pyproject.toml"
