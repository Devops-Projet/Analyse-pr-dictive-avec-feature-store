import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_engine, get_model_loader
from api.main import app
from feature_store.registry import features_for
from models.common.serving import ModelUnavailableError, ServedModel
from models.common.training import build_pipeline

MODELS = {"credit_scoring": "scoring", "marketing_propensity": "marketing"}


class FakeLoader:
    """Remplace le registre MLflow : un modèle entraîné en mémoire par nom."""

    def __init__(self, feature_set_version, available=True):
        self.available = available
        rng = np.random.default_rng(0)
        self.models = {}
        for name, consumer in MODELS.items():
            columns = features_for(consumer)
            X = pd.DataFrame(rng.normal(100, 50, (200, len(columns))), columns=columns)
            y = (X.iloc[:, 0] > 100).astype(int)
            model = build_pipeline({"C": 1.0}, seed=0).fit(X, y)
            self.models[name] = ServedModel(name, "3", model, feature_set_version)

    def get(self, name):
        if not self.available:
            raise ModelUnavailableError(f"Aucune version de {name} en production")
        return self.models[name]


@pytest.fixture
def make_client(engine, loaded):
    def _make(**loader_kwargs):
        loader = FakeLoader(loaded["version"], **loader_kwargs)
        app.dependency_overrides[get_engine] = lambda: engine
        app.dependency_overrides[get_model_loader] = lambda: loader
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("route", "name"), [("scoring", "credit_scoring"), ("marketing", "marketing_propensity")]
)
def test_prediction(make_client, loaded, route, name):
    response = make_client().post(f"/predict/{route}", json={"client_id": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == name
    assert body["model_version"] == "3"
    assert body["feature_set_version"] == loaded["version"]
    assert 0 <= body["probability"] <= 1
    assert body["prediction"] == int(body["probability"] >= 0.5)


def test_prediction_avec_valeur_manquante(make_client):
    # Le client 1 a une valeur manquante (solde_moyen_30j) à l'instantané du 2025-11-01.
    response = make_client().post(
        "/predict/scoring", json={"client_id": 1, "as_of": "2025-11-15T00:00:00"}
    )
    assert response.status_code == 200
    assert response.json()["event_timestamp"] == "2025-11-01T00:00:00"


def test_client_inconnu(make_client):
    assert make_client().post("/predict/scoring", json={"client_id": 999}).status_code == 404


def test_requete_invalide(make_client):
    client = make_client()
    assert client.post("/predict/scoring", json={"client_id": 0}).status_code == 422
    assert client.post("/predict/scoring", json={}).status_code == 422


def test_aucun_modele_en_production(make_client):
    response = make_client(available=False).post("/predict/marketing", json={"client_id": 1})
    assert response.status_code == 503
    assert "marketing_propensity" in response.json()["detail"]


def test_version_du_store_du_modele_absente(make_client):
    client = make_client()
    loader = app.dependency_overrides[get_model_loader]()
    served = loader.models["credit_scoring"]
    loader.models["credit_scoring"] = ServedModel(served.name, "3", served.model, "v-disparue")
    response = client.post("/predict/scoring", json={"client_id": 1})
    assert response.status_code == 503
