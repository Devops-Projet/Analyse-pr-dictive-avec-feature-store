"""Chargement des modèles en production pour le service de prédiction."""

import threading
from dataclasses import dataclass

import mlflow
from mlflow.tracking import MlflowClient
from sklearn.pipeline import Pipeline

from models.common.registry import PRODUCTION, alias_version


class ModelUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class ServedModel:
    name: str
    version: str
    model: Pipeline
    feature_set_version: str

    @property
    def features(self) -> list[str]:
        return list(self.model.feature_names_in_)


class ModelLoader:
    """Résout l'alias `production` à chaque appel et garde en cache les versions déjà chargées.

    Un retour arrière (changement d'alias) est donc pris en compte sans redémarrer l'API.
    """

    def __init__(self, client: MlflowClient | None = None):
        self.client = client or MlflowClient()
        self._cache: dict[tuple[str, str], ServedModel] = {}
        self._lock = threading.Lock()

    def get(self, name: str) -> ServedModel:
        try:
            version = alias_version(self.client, name, PRODUCTION)
        except Exception as e:  # registre injoignable
            raise ModelUnavailableError(f"Registre MLflow injoignable : {e}") from e
        if version is None:
            raise ModelUnavailableError(f"Aucune version de {name} en production")

        with self._lock:
            if (name, version) not in self._cache:
                run_id = self.client.get_model_version(name, version).run_id
                tags = self.client.get_run(run_id).data.tags
                self._cache[(name, version)] = ServedModel(
                    name=name,
                    version=version,
                    model=mlflow.sklearn.load_model(f"models:/{name}/{version}"),
                    feature_set_version=tags["feature_set_version"],
                )
            return self._cache[(name, version)]
