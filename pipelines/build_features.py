"""Calcule les variables du store pour chaque date d'instantané."""

from pathlib import Path

import pandas as pd
import yaml

from feature_store.registry import FEATURE_NAMES
from feature_store.transformations import build_features

RAW_DIR = Path("data/raw")
FEATURES_PATH = Path("data/features/features.csv")


def main() -> None:
    params = yaml.safe_load(Path("params.yaml").read_text(encoding="utf-8"))
    tables = {f.stem: pd.read_csv(f) for f in sorted(RAW_DIR.glob("*.csv"))}
    features = build_features(tables, params["features"]["snapshots"])

    FEATURES_PATH.parent.mkdir(parents=True, exist_ok=True)
    features.round(dict.fromkeys(FEATURE_NAMES, 4)).to_csv(
        FEATURES_PATH, index=False, date_format="%Y-%m-%d"
    )
    print(f"{len(features)} lignes, {features['client_id'].nunique()} clients")


if __name__ == "__main__":
    main()
