"""Écriture d'un jeu de variables calculé dans le feature store."""

import io
import json

import pandas as pd
from sqlalchemy import Engine, text

from feature_store.db import init_schema
from feature_store.registry import FEATURE_NAMES, register_definitions


def version_from_hash(data_hash: str) -> str:
    return f"v-{data_hash[:12]}"


def materialize(
    engine: Engine, features: pd.DataFrame, data_hash: str, params: dict | None = None
) -> dict:
    """Charge `features` (format large) sous une version ; recharger la même version la remplace."""
    version = version_from_hash(data_hash)
    long = features.melt(
        id_vars=["client_id", "event_timestamp"],
        value_vars=FEATURE_NAMES,
        var_name="feature_name",
        value_name="value",
    )
    long.insert(0, "version", version)
    buffer = io.StringIO()
    long[["version", "client_id", "feature_name", "event_timestamp", "value"]].to_csv(
        buffer, index=False, header=False, date_format="%Y-%m-%d %H:%M:%S"
    )
    buffer.seek(0)

    entity_ids = sorted(int(i) for i in features["client_id"].unique())
    resume = {
        "version": version,
        "data_hash": data_hash,
        "n_entities": len(entity_ids),
        "n_values": len(long),
    }

    init_schema(engine)
    with engine.begin() as conn:
        register_definitions(conn)
        conn.execute(
            text("INSERT INTO entities (entity_id) VALUES (:id) ON CONFLICT DO NOTHING"),
            [{"id": i} for i in entity_ids],
        )
        conn.execute(
            text("""
                INSERT INTO feature_set_versions
                    (version, data_hash, params, n_entities, n_values)
                VALUES (:version, :data_hash, CAST(:params AS JSONB), :n_entities, :n_values)
                ON CONFLICT (version) DO UPDATE SET
                    params = EXCLUDED.params,
                    n_entities = EXCLUDED.n_entities,
                    n_values = EXCLUDED.n_values,
                    computed_at = now()
                """),
            {**resume, "params": json.dumps(params or {})},
        )
        conn.execute(text("DELETE FROM feature_values WHERE version = :v"), {"v": version})
        with conn.connection.cursor() as cursor:
            cursor.copy_expert(
                "COPY feature_values "
                "(version, entity_id, feature_name, event_timestamp, value) FROM STDIN WITH CSV",
                buffer,
            )
    return resume
