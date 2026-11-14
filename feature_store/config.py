"""Lecture de la configuration depuis les variables d'environnement."""

import os
from dataclasses import dataclass

from sqlalchemy.engine import URL

REQUIRED = ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg2",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


def get_settings() -> Settings:
    """Échoue immédiatement si une variable obligatoire manque, plutôt que de se connecter
    avec une valeur vide et d'échouer plus loin avec un message trompeur."""
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        raise ConfigError(
            f"Variables d'environnement manquantes : {', '.join(missing)}. "
            "Copier .env.example vers .env et les renseigner."
        )
    port = os.environ.get("POSTGRES_PORT", "5432")
    if not port.isdigit():
        raise ConfigError(f"POSTGRES_PORT doit être un nombre, reçu : {port!r}")
    return Settings(
        postgres_host=os.environ["POSTGRES_HOST"],
        postgres_port=int(port),
        postgres_db=os.environ["POSTGRES_DB"],
        postgres_user=os.environ["POSTGRES_USER"],
        postgres_password=os.environ["POSTGRES_PASSWORD"],
    )
