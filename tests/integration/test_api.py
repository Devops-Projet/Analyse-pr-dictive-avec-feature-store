import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_engine
from api.main import app
from feature_store.registry import FEATURE_NAMES


@pytest.fixture
def client(engine, loaded):
    app.dependency_overrides[get_engine] = lambda: engine
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_variables_d_un_client(client, loaded):
    response = client.get("/features/1")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == loaded["version"]
    assert body["event_timestamp"] == "2025-12-01T00:00:00"
    assert set(body["features"]) == set(FEATURE_NAMES)
    assert body["features"]["age"] == 101


def test_lecture_a_une_date(client):
    body = client.get("/features/1", params={"as_of": "2025-11-15T00:00:00Z"}).json()
    assert body["event_timestamp"] == "2025-11-01T00:00:00"
    assert body["features"]["solde_moyen_30j"] is None


def test_selection_de_variables(client):
    response = client.get("/features/1", params={"features": ["age", "revenu_mensuel"]})
    assert set(response.json()["features"]) == {"age", "revenu_mensuel"}


def test_client_inconnu(client):
    assert client.get("/features/999").status_code == 404


def test_client_id_invalide(client):
    assert client.get("/features/0").status_code == 422
    assert client.get("/features/abc").status_code == 422


def test_version_inconnue(client):
    assert client.get("/features/1", params={"version": "v-inconnue"}).status_code == 404


def test_variable_inconnue(client):
    response = client.get("/features/1", params={"features": ["inexistante"]})
    assert response.status_code == 400


def test_lot_de_clients(client, loaded):
    response = client.post("/features/batch", json={"client_ids": [2, 999, 1, 2]})
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == loaded["version"]
    assert [r["client_id"] for r in body["results"]] == [2, 1]
    assert body["missing"] == [999]


def test_lot_vide_refuse(client):
    assert client.post("/features/batch", json={"client_ids": []}).status_code == 422


def test_lot_trop_grand_refuse(client):
    ids = list(range(1, 1002))
    assert client.post("/features/batch", json={"client_ids": ids}).status_code == 422


def test_catalogue_et_versions(client, loaded):
    definitions = client.get("/features/definitions").json()
    assert {d["name"] for d in definitions} == set(FEATURE_NAMES)
    versions = client.get("/features/versions").json()
    assert [v["version"] for v in versions] == [loaded["version"]]


def test_documentation_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/features/{client_id}", "/features/batch", "/health"} <= set(paths)
