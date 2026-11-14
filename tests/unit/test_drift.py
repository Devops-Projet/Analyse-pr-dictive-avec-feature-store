import numpy as np
import pandas as pd
import pytest

from feature_store.registry import FEATURE_NAMES
from monitoring.drift import compute_drift, psi

THRESHOLDS = {"psi_warning": 0.1, "psi_alert": 0.25, "ks_pvalue": 0.01}


def test_psi_nul_pour_deux_distributions_identiques():
    serie = pd.Series(np.random.default_rng(0).normal(size=2000))
    assert psi(serie, serie) == pytest.approx(0, abs=1e-6)


def test_psi_eleve_pour_une_distribution_decalee():
    rng = np.random.default_rng(0)
    assert psi(pd.Series(rng.normal(0, 1, 2000)), pd.Series(rng.normal(1, 1, 2000))) > 0.25


def test_psi_variable_discrete():
    reference = pd.Series([0] * 500 + [1] * 500)
    assert psi(reference, reference) == pytest.approx(0, abs=1e-6)
    assert psi(reference, pd.Series([0] * 900 + [1] * 100)) > 0.25


def test_psi_ignore_les_valeurs_manquantes():
    serie = pd.Series([1.0, 2.0, np.nan] * 300)
    assert psi(serie, serie) == pytest.approx(0, abs=1e-6)


def _snapshots(shift: float) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    frames = []
    for date, decalage in (("2025-10-01", 0.0), ("2026-01-01", shift)):
        values = {name: rng.normal(decalage, 1, 1000) for name in FEATURE_NAMES}
        frames.append(pd.DataFrame({"event_timestamp": date, **values}))
    return pd.concat(frames, ignore_index=True)


def test_rapport_stable_sans_derive():
    rows = compute_drift(_snapshots(0.0), "2025-10-01", "2026-01-01", THRESHOLDS)
    assert len(rows) == len(FEATURE_NAMES)
    assert {r["status"] for r in rows} <= {"stable", "avertissement"}
    assert sum(r["status"] == "stable" for r in rows) >= len(FEATURE_NAMES) - 2


def test_rapport_en_alerte_avec_derive():
    rows = compute_drift(_snapshots(1.5), "2025-10-01", "2026-01-01", THRESHOLDS)
    assert all(r["status"] == "alerte" for r in rows)


def test_instantane_absent():
    with pytest.raises(ValueError, match="Instantané absent"):
        compute_drift(_snapshots(0.0), "2024-01-01", "2026-01-01", THRESHOLDS)
