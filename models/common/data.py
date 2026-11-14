"""Construction des jeux d'entraînement à partir du feature store."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sqlalchemy import Engine

from feature_store.registry import features_for
from feature_store.retrieval import get_historical_features, resolve_version

CLIENTS_PATH = Path("data/raw/clients.csv")


@dataclass
class TrainingSet:
    X: pd.DataFrame
    y: pd.Series
    feature_version: str

    def split(self, test_size: float, seed: int):
        """Découpage stratifié et déterministe : le même pour l'entraînement et l'évaluation."""
        return train_test_split(
            self.X, self.y, test_size=test_size, random_state=seed, stratify=self.y
        )


def load_training_set(
    engine: Engine,
    consumer: str,
    target: str,
    label_date: str,
    version: str | None = None,
    clients_path: Path = CLIENTS_PATH,
) -> TrainingSet:
    """Variables lues dans le store au point dans le temps `label_date`, cibles lues à part.

    Aucune variable n'est recalculée ici : le modèle consomme uniquement le store.
    """
    labels = pd.read_csv(clients_path, usecols=["client_id", target])
    with engine.connect() as conn:
        version = resolve_version(conn, version)

    features = features_for(consumer)
    entity_df = labels[["client_id"]].assign(event_timestamp=pd.Timestamp(label_date))
    historical = get_historical_features(engine, entity_df, version, features)

    # Les clients sans instantané antérieur à la date d'étiquetage sont écartés.
    known = historical["feature_timestamp"].notna().to_numpy()
    return TrainingSet(
        X=historical.loc[known, features].reset_index(drop=True),
        y=labels.loc[known, target].reset_index(drop=True),
        feature_version=version,
    )
