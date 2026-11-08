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
