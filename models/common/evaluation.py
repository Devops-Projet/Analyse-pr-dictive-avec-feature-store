"""Métriques de classification communes aux modèles consommateurs."""

import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score


def compute_metrics(y_true, proba, threshold: float = 0.5) -> dict[str, float]:
    proba = np.asarray(proba)
    predicted = (proba >= threshold).astype(int)
    return {
        "auc": round(float(roc_auc_score(y_true, proba)), 4),
        "f1": round(float(f1_score(y_true, predicted, zero_division=0)), 4),
        "precision": round(float(precision_score(y_true, predicted, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, predicted, zero_division=0)), 4),
    }
