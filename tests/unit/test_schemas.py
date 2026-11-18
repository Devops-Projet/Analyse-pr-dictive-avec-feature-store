from datetime import datetime

import pytest
from pydantic import ValidationError

from api.schemas import MAX_BATCH, BatchRequest, PredictionRequest, PredictionResponse


def test_lot_valide_avec_valeurs_par_defaut():
    request = BatchRequest(client_ids=[1, 2, 3])
    assert request.version is None
    assert request.as_of is None
    assert request.features is None


@pytest.mark.parametrize("client_ids", [[], list(range(MAX_BATCH + 1))])
def test_taille_du_lot_bornee(client_ids):
    with pytest.raises(ValidationError):
        BatchRequest(client_ids=client_ids)


def test_lot_de_taille_maximale_accepte():
    assert len(BatchRequest(client_ids=list(range(MAX_BATCH))).client_ids) == MAX_BATCH


def test_date_de_lecture_convertie():
    request = BatchRequest(client_ids=[1], as_of="2025-11-15T00:00:00")
    assert request.as_of == datetime(2025, 11, 15)


@pytest.mark.parametrize("client_id", [0, -1, "abc"])
def test_identifiant_client_invalide_refuse(client_id):
    with pytest.raises(ValidationError):
        PredictionRequest(client_id=client_id)


def _prediction(probability: float) -> dict:
    return {
        "client_id": 1,
        "model": "credit_scoring",
        "model_version": "1",
        "feature_set_version": "v-6df062c911ba",
        "event_timestamp": datetime(2026, 1, 1),
        "probability": probability,
        "prediction": int(probability >= 0.5),
    }


@pytest.mark.parametrize("probability", [0.0, 0.5, 1.0])
def test_probabilite_entre_0_et_1_acceptee(probability):
    assert PredictionResponse(**_prediction(probability)).probability == probability


@pytest.mark.parametrize("probability", [-0.01, 1.01])
def test_probabilite_hors_bornes_refusee(probability):
    with pytest.raises(ValidationError):
        PredictionResponse(**_prediction(probability))
