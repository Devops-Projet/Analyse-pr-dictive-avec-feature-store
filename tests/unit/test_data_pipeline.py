import pandas as pd
import pytest

from pipelines.generate_data import generate
from pipelines.validate_data import validate

CONFIG = {
    "n_clients": 200,
    "date_reference": "2026-01-01",
    "historique_jours": 365,
    "transactions_par_mois": 4,
}


@pytest.fixture
def tables():
    return generate(42, CONFIG)


def test_generation_reproductible(tables):
    autres = generate(42, CONFIG)
    for nom, table in tables.items():
        pd.testing.assert_frame_equal(table, autres[nom])


def test_seed_differente_change_les_donnees(tables):
    autres = generate(7, CONFIG)
    assert not tables["clients"]["revenu_mensuel"].equals(autres["clients"]["revenu_mensuel"])


def test_donnees_generees_valides(tables):
    assert validate(tables, CONFIG["date_reference"]) == []


def test_solde_cumule_les_montants(tables):
    transactions = tables["transactions"]
    compte = transactions[transactions["compte_id"] == transactions["compte_id"].iloc[0]]
    ecarts = compte["solde_apres"].diff().dropna() - compte["montant"].iloc[1:]
    assert ecarts.abs().max() < 0.02


def test_detecte_table_absente(tables):
    del tables["contacts"]
    assert "contacts : table absente" in validate(tables, CONFIG["date_reference"])


def test_detecte_colonne_manquante(tables):
    tables["clients"] = tables["clients"].drop(columns="defaut")
    assert any("colonnes manquantes" in e for e in validate(tables, CONFIG["date_reference"]))


def test_detecte_doublons(tables):
    tables["clients"].loc[1, "client_id"] = tables["clients"].loc[0, "client_id"]
    assert "clients : doublons sur client_id" in validate(tables, CONFIG["date_reference"])


def test_detecte_reference_inconnue(tables):
    tables["comptes"].loc[0, "client_id"] = 999999
    assert "comptes : client_id inconnu dans clients" in validate(tables, CONFIG["date_reference"])


def test_detecte_date_future(tables):
    tables["contacts"].loc[0, "date_contact"] = pd.Timestamp("2030-01-01")
    erreurs = validate(tables, CONFIG["date_reference"])
    assert "contacts : date_contact postérieure à la date de référence" in erreurs


def test_detecte_valeur_manquante(tables):
    tables["clients"].loc[0, "revenu_mensuel"] = None
    assert "clients : 1 valeurs manquantes" in validate(tables, CONFIG["date_reference"])
