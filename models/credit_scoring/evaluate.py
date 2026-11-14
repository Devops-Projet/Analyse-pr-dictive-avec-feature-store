"""Évalue la dernière version entraînée et décide de sa mise en production."""

from models.common.training import evaluate
from models.credit_scoring.train import SPEC

if __name__ == "__main__":
    evaluate(SPEC)
