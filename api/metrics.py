"""Métriques de l'API au format texte Prometheus, sans dépendance supplémentaire."""

import threading
import time
from collections import defaultdict

from fastapi import FastAPI, Request

BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.requests = defaultdict(int)  # (method, route, status) -> nombre
        self.duration_buckets = defaultdict(lambda: [0] * len(BUCKETS))  # route -> cumul
        self.duration_sum = defaultdict(float)
        self.duration_count = defaultdict(int)
        self.predictions = defaultdict(int)  # (model, version, prediction) -> nombre

    def observe_request(self, method: str, route: str, status: int, seconds: float) -> None:
        with self._lock:
            self.requests[(method, route, str(status))] += 1
            self.duration_sum[route] += seconds
            self.duration_count[route] += 1
            buckets = self.duration_buckets[route]
            for i, bound in enumerate(BUCKETS):
                if seconds <= bound:
                    buckets[i] += 1

    def observe_prediction(self, model: str, version: str, prediction: int) -> None:
        with self._lock:
            self.predictions[(model, version, str(prediction))] += 1

    def render(self, gauges: list[tuple[str, str, dict, float]]) -> str:
        """`gauges` : (nom, aide, labels, valeur) calculées au moment de la collecte."""
        lines = [
            "# HELP http_requests_total Requêtes HTTP traitées",
            "# TYPE http_requests_total counter",
        ]
        with self._lock:
            for (method, route, status), count in sorted(self.requests.items()):
                labels = _labels(method=method, route=route, status=status)
                lines.append(f"http_requests_total{labels} {count}")

            lines += [
                "# HELP http_request_duration_seconds Durée de traitement des requêtes",
                "# TYPE http_request_duration_seconds histogram",
            ]
            for route in sorted(self.duration_count):
                for bound, count in zip(BUCKETS, self.duration_buckets[route], strict=True):
                    labels = _labels(route=route, le=str(bound))
                    lines.append(f"http_request_duration_seconds_bucket{labels} {count}")
                total = self.duration_count[route]
                lines.append(
                    f"http_request_duration_seconds_bucket{_labels(route=route, le='+Inf')} {total}"
                )
                lines.append(
                    f"http_request_duration_seconds_sum{_labels(route=route)} "
                    f"{self.duration_sum[route]:.6f}"
                )
                lines.append(f"http_request_duration_seconds_count{_labels(route=route)} {total}")

            lines += [
                "# HELP predictions_total Prédictions servies par modèle, version et classe",
                "# TYPE predictions_total counter",
            ]
            for (model, version, prediction), count in sorted(self.predictions.items()):
                labels = _labels(model=model, version=version, prediction=prediction)
                lines.append(f"predictions_total{labels} {count}")

        for name, help_text, labels, value in gauges:
            lines += [f"# HELP {name} {help_text}", f"# TYPE {name} gauge"]
            lines.append(f"{name}{_labels(**labels)} {value}")
        return "\n".join(lines) + "\n"


def _labels(**labels: str) -> str:
    if not labels:
        return ""
    escaped = (
        f'{k}="{str(v).replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"'
        for k, v in labels.items()
    )
    return "{" + ",".join(escaped) + "}"


METRICS = Metrics()


def install(app: FastAPI) -> None:
    """Mesure chaque requête ; le libellé `route` est le modèle de chemin (/features/{client_id})
    et non le chemin réel, pour garder un nombre de séries borné."""

    @app.middleware("http")
    async def measure(request: Request, call_next):
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            path = getattr(route, "path", "inconnue")
            if path != "/metrics":
                METRICS.observe_request(request.method, path, status, time.perf_counter() - start)
