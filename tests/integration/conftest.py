import uuid

import pandas as pd
import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from feature_store.db import get_engine
from feature_store.materialize import materialize
from feature_store.registry import FEATURE_NAMES

SNAPSHOTS = ["2025-11-01", "2025-12-01"]


@pytest.fixture
def engine():
    """Moteur limité à un schéma PostgreSQL temporaire, supprimé après le test."""
    admin = get_engine()
    try:
        with admin.connect():
            pass
    except OperationalError:
        pytest.skip("PostgreSQL indisponible : lancer les tests avec `make test`")

    schema = f"test_{uuid.uuid4().hex[:8]}"
    with admin.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA {schema}"))
    engine = get_engine(schema=schema)
    yield engine
    engine.dispose()
    with admin.begin() as conn:
        conn.execute(text(f"DROP SCHEMA {schema} CASCADE"))
    admin.dispose()


def make_features(offset: float = 0.0) -> pd.DataFrame:
    """Deux clients, deux instantanés ; la valeur encode le client et la date."""
    rows = []
    for i, snapshot in enumerate(SNAPSHOTS):
        for client_id in (1, 2):
            valeur = client_id * 100 + i + offset
            rows.append(
                {
                    "client_id": client_id,
                    "event_timestamp": pd.Timestamp(snapshot),
                    **{nom: valeur for nom in FEATURE_NAMES},
                }
            )
    features = pd.DataFrame(rows)
    features.loc[0, "solde_moyen_30j"] = None
    return features


@pytest.fixture
def loaded(engine):
    """Store chargé avec une version ; retourne son résumé."""
    return materialize(engine, make_features(), "a" * 32)
