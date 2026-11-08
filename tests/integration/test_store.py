import math
from datetime import datetime

import pandas as pd
import pytest
from sqlalchemy import text

from feature_store.materialize import materialize
from feature_store.registry import FEATURE_NAMES, list_definitions
from feature_store.retrieval import (
    UnknownVersionError,
    get_historical_features,
    get_online_features,
    list_versions,
)
from tests.integration.conftest import make_features


def test_chargement_enregistre_version_et_definitions(engine, loaded):
    assert loaded["version"] == "v-aaaaaaaaaaaa"
    assert loaded["n_entities"] == 2
    assert loaded["n_values"] == 4 * len(FEATURE_NAMES)
    assert [d["name"] for d in list_definitions(engine)] == sorted(FEATURE_NAMES)
    assert [v["version"] for v in list_versions(engine)] == [loaded["version"]]


def test_recharger_la_meme_version_ne_duplique_pas(engine, loaded):
    materialize(engine, make_features(), "a" * 32)
    with engine.connect() as conn:
        total = conn.execute(text("SELECT count(*) FROM feature_values")).scalar()
    assert total == loaded["n_values"]


def test_lecture_en_ligne_renvoie_le_dernier_instantane(engine, loaded):
    version, result = get_online_features(engine, [1, 2])
    assert version == loaded["version"]
    assert result[1]["event_timestamp"] == datetime(2025, 12, 1)
    assert result[1]["features"]["age"] == 101
    assert result[2]["features"]["age"] == 201


def test_lecture_en_ligne_au_point_dans_le_temps(engine, loaded):
    _, result = get_online_features(engine, [1], as_of=datetime(2025, 11, 15))
    assert result[1]["event_timestamp"] == datetime(2025, 11, 1)
    assert result[1]["features"]["age"] == 100
    assert result[1]["features"]["solde_moyen_30j"] is None


def test_lecture_en_ligne_filtre_les_variables(engine, loaded):
    _, result = get_online_features(engine, [1], features=["age", "revenu_mensuel"])
    assert set(result[1]["features"]) == {"age", "revenu_mensuel"}


def test_client_inconnu_absent_du_resultat(engine, loaded):
    _, result = get_online_features(engine, [999])
    assert result == {}


def test_variable_inconnue_refusee(engine, loaded):
    with pytest.raises(ValueError, match="inexistante"):
        get_online_features(engine, [1], features=["inexistante"])


def test_version_inconnue_refusee(engine, loaded):
    with pytest.raises(UnknownVersionError):
        get_online_features(engine, [1], version="v-inconnue")


def test_store_vide_sans_version(engine):
    materialize(engine, make_features(), "b" * 32)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM feature_set_versions"))
    with pytest.raises(UnknownVersionError):
        get_online_features(engine, [1])


def test_versions_distinctes_coexistent(engine, loaded):
    autre = materialize(engine, make_features(offset=0.5), "c" * 32)
    _, ancienne = get_online_features(engine, [1], version=loaded["version"])
    _, nouvelle = get_online_features(engine, [1], version=autre["version"])
    assert ancienne[1]["features"]["age"] == 101
    assert nouvelle[1]["features"]["age"] == 101.5


def test_jointure_historique_sans_fuite(engine, loaded):
    entity_df = pd.DataFrame(
        {
            "client_id": [1, 1, 2, 1],
            "event_timestamp": ["2025-12-15", "2025-11-20", "2025-12-01", "2025-10-01"],
        }
    )
    result = get_historical_features(engine, entity_df, features=["age"])

    assert list(result["client_id"]) == [1, 1, 2, 1]
    assert list(result["age"][:3]) == [101, 100, 201]
    assert math.isnan(result["age"][3])
    assert result["feature_timestamp"][1] == pd.Timestamp("2025-11-01")
