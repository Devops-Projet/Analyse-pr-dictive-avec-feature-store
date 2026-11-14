"""Entraînement, suivi MLflow et décision de mise en production des modèles consommateurs."""

import json
from dataclasses import dataclass
from pathlib import Path

import mlflow
import yaml
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from feature_store.db import get_engine
from models.common.data import TrainingSet, load_training_set
from models.common.evaluation import compute_metrics
from models.common.registry import PRODUCTION, alias_version, promote

REPORTS_DIR = Path("reports")
# Format skops (sans pickle arbitraire) : seul ce type supplémentaire est autorisé.
SKOPS_TRUSTED_TYPES = ["numpy.dtype"]


@dataclass(frozen=True)
class ModelSpec:
    name: str  # nom dans le registre MLflow et dossier sous models/
    consumer: str  # clé dans params.yaml et dans le registre des variables
    target: str

    @property
    def run_path(self) -> Path:
        return Path("models") / self.name / "last_run.json"

    @property
    def report_path(self) -> Path:
        return REPORTS_DIR / f"{self.name}.json"


def load_params() -> dict:
    return yaml.safe_load(Path("params.yaml").read_text(encoding="utf-8"))


def build_pipeline(hyperparams: dict, seed: int) -> Pipeline:
    """Régression logistique pondérée : retenue pour les deux modèles après comparaison
    (voir docs/modeles.md)."""
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    C=hyperparams["C"], class_weight="balanced", max_iter=1000, random_state=seed
                ),
            ),
        ]
    )


def _hyperparams(spec: ModelSpec, params: dict) -> dict:
    return {k: v for k, v in params["models"][spec.consumer].items() if k != "min_auc"}


def _training_set(spec: ModelSpec, params: dict, version: str | None = None) -> TrainingSet:
    return load_training_set(
        get_engine(), spec.consumer, spec.target, params["models"]["label_date"], version
    )


def train(spec: ModelSpec) -> dict:
    """Entraîne le modèle, trace l'exécution dans MLflow et ajoute une version au registre."""
    params = load_params()
    seed, test_size = params["seed"], params["models"]["test_size"]
    hyperparams = _hyperparams(spec, params)
    data = _training_set(spec, params)
    X_train, X_test, y_train, y_test = data.split(test_size, seed)

    model = build_pipeline(hyperparams, seed).fit(X_train, y_train)
    metrics = compute_metrics(y_test, model.predict_proba(X_test)[:, 1])
    train_auc = compute_metrics(y_train, model.predict_proba(X_train)[:, 1])["auc"]

    mlflow.set_experiment(spec.name)
    with mlflow.start_run() as run:
        mlflow.set_tags({"feature_set_version": data.feature_version, "consumer": spec.consumer})
        mlflow.log_params(
            {
                **hyperparams,
                "model_type": "logistic_regression",
                "seed": seed,
                "test_size": test_size,
                "n_train": len(X_train),
                "n_test": len(X_test),
                "feature_set_version": data.feature_version,
            }
        )
        mlflow.log_metrics({**metrics, "train_auc": train_auc})
        mlflow.log_dict({"features": list(X_train.columns)}, "features.json")
        info = mlflow.sklearn.log_model(
            model,
            name="model",
            registered_model_name=spec.name,
            signature=infer_signature(X_train, model.predict_proba(X_train)[:, 1]),
            input_example=X_train.head(3),
            skops_trusted_types=SKOPS_TRUSTED_TYPES,
        )

    result = {
        "model": spec.name,
        "run_id": run.info.run_id,
        "model_version": str(info.registered_model_version),
        "feature_set_version": data.feature_version,
        "metrics": metrics,
    }
    spec.run_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{spec.name} v{result['model_version']} : {metrics}")
    return result


def decide(
    candidate: str,
    production: str | None,
    candidate_auc: float,
    production_auc: float | None,
    min_auc: float,
) -> tuple[bool, str]:
    """Règle de promotion : AUC >= min_auc ET AUC > AUC de la version en production.

    S'il n'y a pas encore de version en production, le seuil minimal suffit.
    """
    if production == candidate:
        return False, "version déjà en production"
    if candidate_auc < min_auc:
        return False, f"AUC {candidate_auc} inférieure au seuil {min_auc}"
    if production_auc is None:
        return True, "seuil atteint, aucune version en production"
    if candidate_auc <= production_auc:
        return False, f"AUC {candidate_auc} non supérieure à la production ({production_auc})"
    return True, "seuil atteint et meilleure que la production"


def evaluate(spec: ModelSpec) -> dict:
    """Compare la version candidate à la version en production sur le même jeu de test."""
    params = load_params()
    seed, test_size = params["seed"], params["models"]["test_size"]
    min_auc = params["models"][spec.consumer]["min_auc"]
    run = json.loads(spec.run_path.read_text(encoding="utf-8"))
    data = _training_set(spec, params, run["feature_set_version"])
    _, X_test, _, y_test = data.split(test_size, seed)

    def score(version: str) -> dict:
        model = mlflow.sklearn.load_model(f"models:/{spec.name}/{version}")
        return compute_metrics(y_test, model.predict_proba(X_test)[:, 1])

    client = MlflowClient()
    candidate = run["model_version"]
    production = alias_version(client, spec.name, PRODUCTION)
    candidate_metrics = score(candidate)
    production_metrics = score(production) if production and production != candidate else None

    production_auc = production_metrics["auc"] if production_metrics else None
    promoted, reason = decide(
        candidate, production, candidate_metrics["auc"], production_auc, min_auc
    )

    if promoted:
        promote(client, spec.name, candidate)
    client.set_model_version_tag(spec.name, candidate, "decision", "promue" if promoted else reason)

    report = {
        "model": spec.name,
        "candidate_version": candidate,
        "candidate_metrics": candidate_metrics,
        "min_auc": min_auc,
        "production_before": production,
        "production_metrics_before": production_metrics,
        "promoted": promoted,
        "reason": reason,
        "production_after": alias_version(client, spec.name, PRODUCTION),
        "feature_set_version": run["feature_set_version"],
    }
    REPORTS_DIR.mkdir(exist_ok=True)
    spec.report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{spec.name} v{candidate} : {'promue' if promoted else 'non promue'} ({reason})")
    if report["production_after"] is None:
        raise SystemExit(f"{spec.name} : aucune version en production, l'API ne peut pas prédire")
    return report
