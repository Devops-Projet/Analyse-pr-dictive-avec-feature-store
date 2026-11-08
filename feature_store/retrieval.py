"""Lecture des variables : en ligne (dernières valeurs) et historique (point dans le temps)."""

from datetime import datetime

import pandas as pd
from sqlalchemy import Connection, Engine, text

from feature_store.registry import FEATURE_NAMES


class UnknownVersionError(LookupError):
    pass


def _check_features(features: list[str] | None) -> list[str]:
    if not features:
        return FEATURE_NAMES
    inconnues = sorted(set(features) - set(FEATURE_NAMES))
    if inconnues:
        raise ValueError(f"Variables inconnues : {', '.join(inconnues)}")
    return list(features)


def resolve_version(conn: Connection, version: str | None = None) -> str:
    """Retourne `version` si elle existe, ou la plus récente si `version` est absente."""
    if version is None:
        latest = conn.execute(
            text("SELECT version FROM feature_set_versions ORDER BY computed_at DESC LIMIT 1")
        ).scalar()
        if latest is None:
            raise UnknownVersionError("Aucune version de variables n'est chargée")
        return latest
    exists = conn.execute(
        text("SELECT 1 FROM feature_set_versions WHERE version = :v"), {"v": version}
    ).scalar()
    if exists is None:
        raise UnknownVersionError(f"Version inconnue : {version}")
    return version


def list_versions(engine: Engine) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT version, data_hash, n_entities, n_values, computed_at "
                "FROM feature_set_versions ORDER BY computed_at DESC"
            )
        )
        return [dict(row._mapping) for row in rows]


def get_online_features(
    engine: Engine,
    client_ids: list[int],
    version: str | None = None,
    as_of: datetime | None = None,
    features: list[str] | None = None,
) -> tuple[str, dict[int, dict]]:
    """Dernières valeurs connues à `as_of` (par défaut : les plus récentes) pour chaque client.

    Retourne la version utilisée et, pour chaque client trouvé,
    `{"event_timestamp": ..., "features": {nom: valeur}}`.
    """
    features = _check_features(features)
    with engine.connect() as conn:
        version = resolve_version(conn, version)
        rows = conn.execute(
            text("""
                SELECT DISTINCT ON (entity_id, feature_name)
                    entity_id, feature_name, value, event_timestamp
                FROM feature_values
                WHERE version = :version
                  AND entity_id = ANY(:ids)
                  AND feature_name = ANY(:features)
                  AND (CAST(:as_of AS TIMESTAMP) IS NULL OR event_timestamp <= :as_of)
                ORDER BY entity_id, feature_name, event_timestamp DESC
                """),
            {"version": version, "ids": list(client_ids), "features": features, "as_of": as_of},
        )
        result: dict[int, dict] = {}
        for entity_id, name, value, timestamp in rows:
            entry = result.setdefault(entity_id, {"event_timestamp": timestamp, "features": {}})
            entry["features"][name] = value
            entry["event_timestamp"] = max(entry["event_timestamp"], timestamp)
    return version, result


def get_historical_features(
    engine: Engine,
    entity_df: pd.DataFrame,
    version: str | None = None,
    features: list[str] | None = None,
) -> pd.DataFrame:
    """Jointure au point dans le temps pour l'entraînement.

    Pour chaque ligne (`client_id`, `event_timestamp`) de `entity_df`, on prend le dernier
    instantané calculé à cette date ou avant : aucune valeur future ne peut fuiter.
    Les clients sans instantané antérieur gardent des variables manquantes.
    """
    features = _check_features(features)
    with engine.connect() as conn:
        version = resolve_version(conn, version)
        values = pd.read_sql(
            text("""
                SELECT entity_id AS client_id, event_timestamp AS feature_timestamp,
                       feature_name, value
                FROM feature_values
                WHERE version = :version
                  AND entity_id = ANY(:ids)
                  AND feature_name = ANY(:features)
                  AND event_timestamp <= :max_ts
                """),
            conn,
            params={
                "version": version,
                "ids": [int(i) for i in entity_df["client_id"].unique()],
                "features": features,
                "max_ts": pd.Timestamp(entity_df["event_timestamp"].max()).to_pydatetime(),
            },
        )

    wide = (
        values.pivot_table(
            index=["client_id", "feature_timestamp"],
            columns="feature_name",
            values="value",
            dropna=False,
        )
        .reindex(columns=features)
        .reset_index()
        .sort_values("feature_timestamp")
    )
    wide.columns.name = None
    left = entity_df.assign(
        event_timestamp=pd.to_datetime(entity_df["event_timestamp"]),
        _ordre=range(len(entity_df)),
    ).sort_values("event_timestamp")
    joined = pd.merge_asof(
        left,
        wide,
        left_on="event_timestamp",
        right_on="feature_timestamp",
        by="client_id",
        direction="backward",
    )
    return joined.sort_values("_ordre").drop(columns="_ordre").reset_index(drop=True)
