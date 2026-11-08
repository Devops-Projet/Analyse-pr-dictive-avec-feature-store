"""Connexion à PostgreSQL et création du schéma."""

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL

from feature_store.config import get_settings

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_engine(url: URL | str | None = None, schema: str | None = None) -> Engine:
    """Crée un moteur SQLAlchemy ; `schema` isole les tables (utile pour les tests)."""
    connect_args = {"options": f"-csearch_path={schema}"} if schema else {}
    return create_engine(
        url or get_settings().database_url, pool_pre_ping=True, connect_args=connect_args
    )


def init_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(SCHEMA_PATH.read_text(encoding="utf-8"))
