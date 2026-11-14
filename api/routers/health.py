"""Santé, disponibilité et métriques du service."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import Engine

from api.dependencies import get_engine, get_model_loader
from api.metrics import METRICS
from feature_store.retrieval import freshness
from models.common.registry import MODEL_NAMES
from models.common.serving import ModelLoader

router = APIRouter(tags=["health"])
EngineDep = Annotated[Engine, Depends(get_engine)]
LoaderDep = Annotated[ModelLoader, Depends(get_model_loader)]


@router.get("/health")
def health() -> dict[str, str]:
    """Le processus répond (utilisé par le healthcheck Docker)."""
    return {"status": "ok"}


def _checks(engine: Engine, loader: ModelLoader) -> tuple[dict, dict | None]:
    checks = {}
    fresh = None
    try:
        fresh = freshness(engine)
        checks["feature_store"] = "ok" if fresh else "aucune version chargée"
    except Exception as e:
        checks["feature_store"] = f"injoignable : {type(e).__name__}"
    for name in MODEL_NAMES:
        try:
            checks[name] = f"version {loader.get(name).version}"
        except Exception as e:
            checks[name] = f"indisponible : {e}"
    return checks, fresh


@router.get("/ready")
def ready(engine: EngineDep, loader: LoaderDep):
    """Le service peut répondre aux requêtes : store chargé et modèles en production."""
    checks, fresh = _checks(engine, loader)
    ok = checks["feature_store"] == "ok" and all(
        checks[name].startswith("version") for name in MODEL_NAMES
    )
    body = {"status": "ready" if ok else "not_ready", "checks": checks}
    if fresh:
        body["feature_store"] = {
            "version": fresh["version"],
            "computed_at": fresh["computed_at"].isoformat(),
            "latest_snapshot": (
                fresh["latest_snapshot"].isoformat() if fresh["latest_snapshot"] else None
            ),
        }
    return JSONResponse(body, status_code=200 if ok else 503)


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(engine: EngineDep, loader: LoaderDep) -> str:
    """Métriques au format Prometheus : trafic, erreurs, latence, prédictions, fraîcheur."""
    checks, fresh = _checks(engine, loader)
    now = datetime.now(UTC).timestamp()
    gauges = [
        (
            "service_ready",
            "1 si le store est chargé et les deux modèles en production",
            {},
            int(all(c == "ok" or c.startswith("version") for c in checks.values())),
        )
    ]
    for name in MODEL_NAMES:
        version = (
            checks[name].removeprefix("version ") if checks[name].startswith("version") else "0"
        )
        gauges.append(
            (
                "model_production_version",
                "Version en production par modèle",
                {"model": name},
                version,
            )
        )
    if fresh:
        computed = fresh["computed_at"].timestamp()
        gauges += [
            (
                "feature_store_last_load_timestamp_seconds",
                "Date du dernier chargement du store",
                {"version": fresh["version"]},
                computed,
            ),
            (
                "feature_store_last_load_age_seconds",
                "Ancienneté du dernier chargement du store",
                {},
                round(now - computed, 1),
            ),
        ]
        if fresh["latest_snapshot"]:
            snapshot = fresh["latest_snapshot"].replace(tzinfo=UTC).timestamp()
            gauges.append(
                (
                    "feature_store_latest_snapshot_timestamp_seconds",
                    "Date du dernier instantané de variables",
                    {},
                    snapshot,
                )
            )
    return METRICS.render(gauges)
