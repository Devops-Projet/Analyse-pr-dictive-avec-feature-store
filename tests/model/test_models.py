"""Validation des modèles : seuil de performance, format des sorties et cas limites.

Les modèles sont entraînés sur un petit jeu synthétique calculé avec les mêmes transformations
que le store, sans base de données ni MLflow, pour tourner rapidement en CI.
"""

import numpy as np
import pandas as pd
import pytest
import yaml

from feature_store.registry import features_for
from feature_store.transformations import build_features
from models.common.evaluation import compute_metrics
from models.common.training import build_pipeline
from pipelines.generate_data import generate

PARAMS = yaml.safe_load(open("params.yaml", encoding="utf-8"))
LABEL_DATE = PARAMS["models"]["label_date"]
MODELS = [("scoring", "defaut"), ("marketing", "souscription")]


@pytest.fixture(scope="module")
def dataset():
    config = {**PARAMS["data"], "n_clients": 2000}
    tables = generate(PARAMS["seed"], config)
    features = build_features(tables, [LABEL_DATE])
    return features.merge(tables["clients"][["client_id", "defaut", "souscription"]])


@pytest.fixture(scope="module", params=MODELS, ids=[c for c, _ in MODELS])
def trained(request, dataset):
    consumer, target = request.param
    hyperparams = {k: v for k, v in PARAMS["models"][consumer].items() if k != "min_auc"}
    X, y = dataset[features_for(consumer)], dataset[target]
    split = len(X) * 3 // 4
    model = build_pipeline(hyperparams, PARAMS["seed"]).fit(X[:split], y[:split])
    return consumer, model, X[split:], y[split:]


def test_auc_au_dessus_du_seuil(trained):
    consumer, model, X_test, y_test = trained
    auc = compute_metrics(y_test, model.predict_proba(X_test)[:, 1])["auc"]
    assert auc >= PARAMS["models"][consumer]["min_auc"]


def test_probabilites_entre_0_et_1(trained):
    _, model, X_test, _ = trained
    proba = model.predict_proba(X_test)[:, 1]
    assert proba.shape == (len(X_test),)
    assert np.all((proba >= 0) & (proba <= 1))


def test_valeurs_manquantes_acceptees(trained):
    _, model, X_test, _ = trained
    vide = pd.DataFrame(np.nan, index=[0], columns=X_test.columns)
    proba = model.predict_proba(pd.concat([X_test.head(2), vide]))[:, 1]
    assert np.all(np.isfinite(proba))


def test_variables_attendues_dans_l_ordre_du_registre(trained):
    consumer, model, _, _ = trained
    assert list(model.feature_names_in_) == features_for(consumer)


def test_deux_modeles_partagent_des_variables():
    assert set(features_for("scoring")) & set(features_for("marketing"))
