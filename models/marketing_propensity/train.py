"""Entraîne le modèle de propension marketing (souscription à une offre)."""

from models.common.training import ModelSpec, train

SPEC = ModelSpec(name="marketing_propensity", consumer="marketing", target="souscription")

if __name__ == "__main__":
    train(SPEC)
