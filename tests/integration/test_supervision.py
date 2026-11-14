import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_engine, get_model_loader
from api.main import app
from tests.integration.test_predict import FakeLoader


@pytest.fixture
def make_client(engine, loaded):
    def _make(available=True):
        loader = FakeLoader(loaded["version"], available=available)
        app.dependency_overrides[get_engine] = lambda: engine
        app.dependency_overrides[get_model_loader] = lambda: loader
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


def test_pret_quand_store_et_modeles_disponibles(make_client, loaded):
    response = make_client().get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["feature_store"]["version"] == loaded["version"]
    assert body["feature_store"]["latest_snapshot"] == "2025-12-01T00:00:00"


def test_pas_pret_sans_modele_en_production(make_client):
    response = make_client(available=False).get("/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["credit_scoring"].startswith("indisponible")


def test_metriques_prometheus(make_client):
    client = make_client()
    client.get("/features/1")
    client.get("/features/999")
    client.post("/predict/scoring", json={"client_id": 1})
    text = client.get("/metrics").text

    assert 'http_requests_total{method="GET",route="/features/{client_id}",status="200"}' in text
    assert 'route="/features/{client_id}",status="404"' in text
    assert 'http_request_duration_seconds_bucket{route="/predict/scoring",le="+Inf"}' in text
    assert 'predictions_total{model="credit_scoring",version="3"' in text
    assert "service_ready 1" in text
    assert 'model_production_version{model="marketing_propensity"} 3' in text
    assert "feature_store_last_load_age_seconds" in text
    assert "/metrics" not in text.split("predictions_total")[0]


def test_metriques_signalent_un_service_non_pret(make_client):
    text = make_client(available=False).get("/metrics").text
    assert "service_ready 0" in text
