"""Charge les variables calculées dans PostgreSQL et écrit un reçu suivi par DVC."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

from feature_store.db import get_engine
from feature_store.materialize import materialize

FEATURES_PATH = Path("data/features/features.csv")
RECEIPT_PATH = Path("data/features/load_receipt.json")


def file_md5(path: Path) -> str:
    # Même empreinte que celle que DVC enregistre pour ce fichier dans dvc.lock.
    return hashlib.md5(path.read_bytes()).hexdigest()


def main() -> None:
    params = yaml.safe_load(Path("params.yaml").read_text(encoding="utf-8"))
    features = pd.read_csv(FEATURES_PATH, parse_dates=["event_timestamp"])
    resume = materialize(get_engine(), features, file_md5(FEATURES_PATH), params["features"])

    RECEIPT_PATH.write_text(json.dumps(resume, indent=2) + "\n", encoding="utf-8")
    print(f"Version {resume['version']} chargée : {resume['n_values']} valeurs")


if __name__ == "__main__":
    main()
