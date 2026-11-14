"""Contrôle après déploiement : vérifie le parcours réel sur le service démarré.

    API_URL=http://localhost:8000 python scripts/smoke_test.py

Code de sortie 1 au premier contrôle en échec : la livraison doit alors être arrêtée et le
service rétabli (voir docs/runbook.md).
"""

import json
import os
import sys
import urllib.error
import urllib.request

API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
CLIENT_ID = int(os.environ.get("SMOKE_CLIENT_ID", "1"))


def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(
        API_URL + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def check_prediction(body: dict) -> bool:
    return 0 <= body.get("probability", -1) <= 1 and body.get("model_version") is not None


CHECKS = [
    ("service en bonne santé", "GET", "/health", None, 200, lambda b: b == {"status": "ok"}),
    (
        "variables d'un client",
        "GET",
        f"/features/{CLIENT_ID}",
        None,
        200,
        lambda b: len(b.get("features", {})) == 20,
    ),
    ("client inconnu refusé", "GET", "/features/999999999", None, 404, lambda b: True),
    (
        "prédiction scoring",
        "POST",
        "/predict/scoring",
        {"client_id": CLIENT_ID},
        200,
        check_prediction,
    ),
    (
        "prédiction marketing",
        "POST",
        "/predict/marketing",
        {"client_id": CLIENT_ID},
        200,
        check_prediction,
    ),
]


def main() -> int:
    for label, method, path, body, expected, valid in CHECKS:
        try:
            status, payload = call(method, path, body)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"ÉCHEC  {label} : service injoignable ({e})")
            return 1
        if status != expected or not valid(payload):
            print(f"ÉCHEC  {label} : HTTP {status}, réponse {payload}")
            return 1
        print(f"OK     {label}")
    print(f"Tous les contrôles réussis sur {API_URL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
