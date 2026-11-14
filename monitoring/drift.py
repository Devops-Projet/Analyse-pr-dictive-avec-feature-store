"""Détection de dérive entre un instantané de référence et l'instantané le plus récent.

Pour chaque variable : indice de stabilité de population (PSI) et test de Kolmogorov-Smirnov.
Seuils dans `params.yaml` (section `monitoring`). Le rapport est écrit dans reports/drift.json.

Lecture du PSI : < 0,1 stable ; 0,1 à 0,25 dérive modérée (avertissement) ; > 0,25 alerte.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.stats import ks_2samp

from feature_store.registry import FEATURE_NAMES

FEATURES_PATH = Path("data/features/features.csv")
REPORT_PATH = Path("reports/drift.json")
EPSILON = 1e-4
MAX_CATEGORIES = 10


def psi(reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
    reference, current = reference.dropna(), current.dropna()
    if reference.empty or current.empty:
        return float("nan")
    if reference.nunique() <= MAX_CATEGORIES:
        # Variable discrète : comparaison des fréquences de chaque valeur.
        categories = sorted(set(reference) | set(current))
        ref = reference.value_counts(normalize=True).reindex(categories, fill_value=0)
        cur = current.value_counts(normalize=True).reindex(categories, fill_value=0)
    else:
        # Variable continue : classes définies par les quantiles de la référence.
        edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
        edges[0], edges[-1] = -np.inf, np.inf
        ref = pd.Series(np.histogram(reference, edges)[0]) / len(reference)
        cur = pd.Series(np.histogram(current, edges)[0]) / len(current)
    ref, cur = ref.to_numpy() + EPSILON, cur.to_numpy() + EPSILON
    return float(np.sum((cur - ref) * np.log(cur / ref)))


def compute_drift(
    features: pd.DataFrame, reference: str, current: str, thresholds: dict
) -> list[dict]:
    timestamps = pd.to_datetime(features["event_timestamp"])
    ref = features[timestamps == pd.Timestamp(reference)]
    cur = features[timestamps == pd.Timestamp(current)]
    if ref.empty or cur.empty:
        raise ValueError(f"Instantané absent : référence {reference} ou courant {current}")

    rows = []
    for name in FEATURE_NAMES:
        value = psi(ref[name], cur[name])
        a, b = ref[name].dropna(), cur[name].dropna()
        ks = ks_2samp(a, b) if len(a) and len(b) else None
        if value > thresholds["psi_alert"]:
            status = "alerte"
        elif value > thresholds["psi_warning"] or (
            ks is not None and ks.pvalue < thresholds["ks_pvalue"]
        ):
            status = "avertissement"
        else:
            status = "stable"
        rows.append(
            {
                "feature": name,
                "psi": round(value, 4),
                "ks_statistic": round(float(ks.statistic), 4) if ks else None,
                "ks_pvalue": round(float(ks.pvalue), 4) if ks else None,
                "status": status,
            }
        )
    return rows


def main() -> None:
    params = yaml.safe_load(Path("params.yaml").read_text(encoding="utf-8"))["monitoring"]
    features = pd.read_csv(FEATURES_PATH)
    rows = compute_drift(features, params["reference_snapshot"], params["current_snapshot"], params)
    summary = {
        s: sum(r["status"] == s for r in rows) for s in ("stable", "avertissement", "alerte")
    }
    report = {
        "reference_snapshot": params["reference_snapshot"],
        "current_snapshot": params["current_snapshot"],
        "thresholds": {k: params[k] for k in ("psi_warning", "psi_alert", "ks_pvalue")},
        "summary": summary,
        "features": rows,
    }
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Dérive {params['reference_snapshot']} → {params['current_snapshot']} : {summary}")
    for row in rows:
        if row["status"] != "stable":
            detail = f"PSI {row['psi']}, KS p={row['ks_pvalue']}"
            print(f"  {row['status']:13s} {row['feature']} ({detail})")


if __name__ == "__main__":
    main()
