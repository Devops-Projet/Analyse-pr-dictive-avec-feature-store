"""Modèles Pydantic des requêtes et réponses de l'API."""

from datetime import datetime

from pydantic import BaseModel, Field

MAX_BATCH = 1000


class FeatureVector(BaseModel):
    client_id: int
    event_timestamp: datetime = Field(description="Date de l'instantané utilisé")
    features: dict[str, float | None]


class FeatureResponse(FeatureVector):
    version: str


class BatchRequest(BaseModel):
    client_ids: list[int] = Field(min_length=1, max_length=MAX_BATCH)
    version: str | None = Field(None, description="Version du store ; la plus récente si absente")
    as_of: datetime | None = Field(None, description="Date de lecture ; la plus récente si absente")
    features: list[str] | None = Field(None, description="Variables voulues ; toutes si absent")

    model_config = {
        "json_schema_extra": {
            "examples": [{"client_ids": [1, 2, 3], "features": ["age", "revenu_mensuel"]}]
        }
    }


class BatchResponse(BaseModel):
    version: str
    results: list[FeatureVector]
    missing: list[int] = Field(description="Clients sans valeur dans cette version")


class FeatureDefinition(BaseModel):
    name: str
    dtype: str
    description: str
    owner: str
    version: int


class FeatureSetVersion(BaseModel):
    version: str
    data_hash: str
    n_entities: int
    n_values: int
    computed_at: datetime


class PredictionRequest(BaseModel):
    client_id: int = Field(gt=0)
    as_of: datetime | None = Field(None, description="Date de lecture ; la plus récente si absente")

    model_config = {"json_schema_extra": {"examples": [{"client_id": 42}]}}


class PredictionResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    client_id: int
    model: str
    model_version: str
    feature_set_version: str
    event_timestamp: datetime = Field(description="Date de l'instantané de variables utilisé")
    probability: float = Field(ge=0, le=1)
    prediction: int = Field(description="1 si la probabilité atteint le seuil de 0,5")
