import pytest
from mlflow.exceptions import MlflowException

from models.common.evaluation import compute_metrics
from models.common.registry import PREVIOUS, PRODUCTION, promote, rollback, status
from models.common.training import decide


class FakeClient:
    """Registre MLflow en mémoire : uniquement les alias et les tags utilisés."""

    def __init__(self):
        self.aliases, self.tags = {}, {}

    def get_model_version_by_alias(self, name, alias):
        if (name, alias) not in self.aliases:
            raise MlflowException("alias absent")
        return type("Version", (), {"version": self.aliases[(name, alias)]})

    def set_registered_model_alias(self, name, alias, version):
        self.aliases[(name, alias)] = version

    def delete_registered_model_alias(self, name, alias):
        del self.aliases[(name, alias)]

    def set_model_version_tag(self, name, version, key, value):
        self.tags[(name, version, key)] = value


def test_premiere_promotion_sans_version_precedente():
    client = FakeClient()
    promote(client, "m", "1")
    assert status(client, "m") == {PRODUCTION: "1", PREVIOUS: None}


def test_promotion_garde_la_version_precedente():
    client = FakeClient()
    promote(client, "m", "1")
    promote(client, "m", "2")
    assert status(client, "m") == {PRODUCTION: "2", PREVIOUS: "1"}


def test_repromouvoir_la_meme_version_ne_change_rien():
    client = FakeClient()
    promote(client, "m", "1")
    promote(client, "m", "2")
    promote(client, "m", "2")
    assert status(client, "m") == {PRODUCTION: "2", PREVIOUS: "1"}


def test_retour_arriere():
    client = FakeClient()
    promote(client, "m", "1")
    promote(client, "m", "2")
    assert rollback(client, "m") == ("2", "1")
    assert status(client, "m") == {PRODUCTION: "1", PREVIOUS: None}
    assert ("m", "2", "retiree_le") in client.tags


def test_retour_arriere_impossible_sans_version_precedente():
    client = FakeClient()
    promote(client, "m", "1")
    with pytest.raises(RuntimeError, match="aucune version précédente"):
        rollback(client, "m")


@pytest.mark.parametrize(
    ("candidate", "production", "cand_auc", "prod_auc", "attendu"),
    [
        ("1", None, 0.70, None, True),  # première version au-dessus du seuil
        ("1", None, 0.60, None, False),  # sous le seuil
        ("2", "1", 0.72, 0.70, True),  # meilleure que la production
        ("2", "1", 0.70, 0.70, False),  # égale : pas de promotion
        ("2", "1", 0.64, 0.60, False),  # meilleure mais sous le seuil
        ("1", "1", 0.90, 0.90, False),  # déjà en production
    ],
)
def test_regle_de_promotion(candidate, production, cand_auc, prod_auc, attendu):
    promoted, reason = decide(candidate, production, cand_auc, prod_auc, min_auc=0.65)
    assert promoted is attendu
    assert reason


def test_metriques():
    metrics = compute_metrics([0, 0, 1, 1], [0.1, 0.6, 0.4, 0.9])
    assert metrics == {"auc": 0.75, "f1": 0.5, "precision": 0.5, "recall": 0.5}
