"""Entraîne le modèle de scoring crédit (risque de défaut)."""

from models.common.training import ModelSpec, train

SPEC = ModelSpec(name="credit_scoring", consumer="scoring", target="defaut")

if __name__ == "__main__":
    train(SPEC)
