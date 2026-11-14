"""Routes de prédiction : variables lues dans le store, modèle chargé depuis le registre MLflow."""

from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Engine

from api.dependencies import get_engine, get_model_loader
from api.metrics import METRICS
from api.routers.features import naive_utc
from api.schemas import PredictionRequest, PredictionResponse
from feature_store.retrieval import UnknownVersionError, get_online_features
from models.common.serving import ModelLoader, ModelUnavailableError

router = APIRouter(prefix="/predict", tags=["predict"])
EngineDep = Annotated[Engine, Depends(get_engine)]
LoaderDep = Annotated[ModelLoader, Depends(get_model_loader)]
THRESHOLD = 0.5


def _predict(engine: Engine, loader: ModelLoader, name: str, request: PredictionRequest):
    try:
        served = loader.get(name)
    except ModelUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    # Variables lues dans la version du store sur laquelle le modèle a été entraîné.
    try:
        _, result = get_online_features(
            engine,
            [request.client_id],
            served.feature_set_version,
            naive_utc(request.as_of),
            served.features,
        )
    except UnknownVersionError as e:
        detail = f"Version du store du modèle absente : {served.feature_set_version}"
        raise HTTPException(status_code=503, detail=detail) from e
    if request.client_id not in result:
        raise HTTPException(status_code=404, detail=f"Client inconnu : {request.client_id}")

    row = result[request.client_id]
    X = pd.DataFrame([row["features"]], columns=served.features, dtype=float)
    probability = float(served.model.predict_proba(X)[0, 1])
    METRICS.observe_prediction(served.name, served.version, int(probability >= THRESHOLD))
    return PredictionResponse(
        client_id=request.client_id,
        model=served.name,
        model_version=served.version,
        feature_set_version=served.feature_set_version,
        event_timestamp=row["event_timestamp"],
        probability=round(probability, 4),
        prediction=int(probability >= THRESHOLD),
    )


@router.post("/scoring", response_model=PredictionResponse)
def predict_scoring(engine: EngineDep, loader: LoaderDep, request: PredictionRequest):
    """Probabilité de défaut de paiement du client."""
    return _predict(engine, loader, "credit_scoring", request)


@router.post("/marketing", response_model=PredictionResponse)
def predict_marketing(engine: EngineDep, loader: LoaderDep, request: PredictionRequest):
    """Probabilité que le client souscrive à l'offre."""
    return _predict(engine, loader, "marketing_propensity", request)
