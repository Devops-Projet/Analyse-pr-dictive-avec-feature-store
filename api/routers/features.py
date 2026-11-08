"""Routes de récupération des variables du store."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import Engine

from api.dependencies import get_engine
from api.schemas import (
    BatchRequest,
    BatchResponse,
    FeatureDefinition,
    FeatureResponse,
    FeatureSetVersion,
    FeatureVector,
)
from feature_store.registry import list_definitions
from feature_store.retrieval import UnknownVersionError, get_online_features, list_versions

router = APIRouter(prefix="/features", tags=["features"])
EngineDep = Annotated[Engine, Depends(get_engine)]


def _naive_utc(value: datetime | None) -> datetime | None:
    # Les dates du store sont stockées sans fuseau, en UTC.
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _read(engine: Engine, client_ids, version, as_of, features):
    try:
        return get_online_features(engine, client_ids, version, _naive_utc(as_of), features)
    except UnknownVersionError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/definitions", response_model=list[FeatureDefinition])
def definitions(engine: EngineDep):
    """Catalogue des variables disponibles."""
    return list_definitions(engine)


@router.get("/versions", response_model=list[FeatureSetVersion])
def versions(engine: EngineDep):
    """Versions chargées du store, de la plus récente à la plus ancienne."""
    return list_versions(engine)


@router.get("/{client_id}", response_model=FeatureResponse)
def client_features(
    engine: EngineDep,
    client_id: Annotated[int, Path(gt=0)],
    version: str | None = None,
    as_of: datetime | None = None,
    features: Annotated[list[str] | None, Query()] = None,
):
    """Dernières valeurs connues d'un client, à `as_of` si cette date est fournie."""
    version, result = _read(engine, [client_id], version, as_of, features)
    if client_id not in result:
        raise HTTPException(status_code=404, detail=f"Client inconnu : {client_id}")
    return FeatureResponse(client_id=client_id, version=version, **result[client_id])


@router.post("/batch", response_model=BatchResponse)
def batch_features(engine: EngineDep, request: BatchRequest):
    """Variables de plusieurs clients en un seul appel."""
    client_ids = list(dict.fromkeys(request.client_ids))
    version, result = _read(engine, client_ids, request.version, request.as_of, request.features)
    return BatchResponse(
        version=version,
        results=[FeatureVector(client_id=i, **result[i]) for i in client_ids if i in result],
        missing=[i for i in client_ids if i not in result],
    )
