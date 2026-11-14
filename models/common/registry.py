"""Registre MLflow : mise en production, retour arrière et état des modèles.

Deux alias par modèle : `production` (version servie par l'API) et `previous`
(version qui était en production avant la dernière promotion).

    python -m models.common.registry status <modèle>
    python -m models.common.registry rollback <modèle>
    python -m models.common.registry check     # code 1 si un modèle n'a pas de production
"""

import sys
from datetime import UTC, datetime

from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

PRODUCTION = "production"
PREVIOUS = "previous"
MODEL_NAMES = ("credit_scoring", "marketing_propensity")


def alias_version(client: MlflowClient, name: str, alias: str) -> str | None:
    try:
        return client.get_model_version_by_alias(name, alias).version
    except MlflowException:
        return None


def promote(client: MlflowClient, name: str, version: str) -> None:
    current = alias_version(client, name, PRODUCTION)
    if current == version:
        return
    if current is not None:
        client.set_registered_model_alias(name, PREVIOUS, current)
    client.set_registered_model_alias(name, PRODUCTION, version)


def rollback(client: MlflowClient, name: str) -> tuple[str | None, str]:
    """Remet en production la version précédente ; retourne (version retirée, version rétablie)."""
    previous = alias_version(client, name, PREVIOUS)
    if previous is None:
        raise RuntimeError(f"{name} : aucune version précédente à rétablir")
    current = alias_version(client, name, PRODUCTION)
    client.set_registered_model_alias(name, PRODUCTION, previous)
    client.delete_registered_model_alias(name, PREVIOUS)
    if current is not None:
        client.set_model_version_tag(
            name, current, "retiree_le", datetime.now(UTC).isoformat(timespec="seconds")
        )
    return current, previous


def status(client: MlflowClient, name: str) -> dict[str, str | None]:
    return {alias: alias_version(client, name, alias) for alias in (PRODUCTION, PREVIOUS)}


def main(argv: list[str]) -> int:
    if argv == ["check"]:
        missing = [n for n in MODEL_NAMES if alias_version(MlflowClient(), n, PRODUCTION) is None]
        if missing:
            print(f"Aucune version en production : {', '.join(missing)}", file=sys.stderr)
            return 1
        print("Tous les modèles ont une version en production")
        return 0
    if len(argv) != 2 or argv[0] not in ("status", "rollback") or argv[1] not in MODEL_NAMES:
        print(__doc__, file=sys.stderr)
        return 2
    action, name = argv
    client = MlflowClient()
    if action == "rollback":
        try:
            retired, restored = rollback(client, name)
        except RuntimeError as e:
            print(e, file=sys.stderr)
            return 1
        print(f"{name} : version {retired} retirée, version {restored} remise en production")
    else:
        print(f"{name} : {status(client, name)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
