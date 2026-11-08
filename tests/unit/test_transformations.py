import math

import pandas as pd
import pytest

from feature_store.registry import FEATURE_NAMES
from feature_store.transformations import build_features, compute_features, parse_dates

AS_OF = "2026-01-01"


def _tables_brutes():
    return {
        "clients": pd.DataFrame(
            {
                "client_id": [1, 2, 3],
                "date_naissance": ["1990-06-15", "1980-01-01", "2000-01-01"],
                "date_entree": ["2020-03-10", "2015-01-01", "2026-02-01"],
                "revenu_mensuel": [2000.0, 3000.0, 1500.0],
                "utilise_app_mobile": [True, False, True],
                "nb_produits": [2, 1, 1],
                "defaut": [0, 1, 0],
                "souscription": [1, 0, 0],
            }
        ),
        "comptes": pd.DataFrame({"compte_id": [10, 11, 20], "client_id": [1, 1, 2]}),
        "transactions": pd.DataFrame(
            {
                "transaction_id": range(1, 7),
                "compte_id": [10, 10, 10, 11, 10, 20],
                "date_transaction": [
                    "2025-12-10",
                    "2025-12-20",
                    "2025-12-25",
                    "2025-12-15",
                    "2026-01-05",  # après la date de calcul : ignorée
                    "2025-11-01",
                ],
                "montant": [1000.0, -1500.0, -100.0, -50.0, -9999.0, 500.0],
                "solde_apres": [800.0, -700.0, -800.0, 200.0, -10799.0, 1500.0],
            }
        ),
        "credits": pd.DataFrame(
            {
                "credit_id": [1, 2],
                "client_id": [1, 1],
                "date_debut": ["2024-01-01", "2026-06-01"],
                "mensualite": [400.0, 999.0],
            }
        ),
        "retards": pd.DataFrame(
            {
                "client_id": [1, 1, 2],
                "date_echeance": ["2025-06-01", "2024-06-01", "2025-12-31"],
                "jours_retard": [10, 60, 5],
            }
        ),
        "contacts": pd.DataFrame(
            {"client_id": [2, 2], "date_contact": ["2025-12-01", "2025-09-01"]}
        ),
    }


@pytest.fixture
def tables():
    return parse_dates(_tables_brutes())


@pytest.fixture
def features(tables):
    return compute_features(tables, AS_OF).set_index("client_id")


def test_colonnes_conformes_au_registre(features):
    assert list(features.columns) == ["event_timestamp", *FEATURE_NAMES]


def test_client_pas_encore_entre_exclu(features):
    assert list(features.index) == [1, 2]


def test_age_et_anciennete(features):
    assert features.loc[1, "age"] == 35
    assert features.loc[1, "anciennete_mois"] == 69


def test_transactions_futures_ignorees(features):
    assert features.loc[1, "nb_transactions_30j"] == 4
    assert features.loc[1, "montant_debits_30j"] == 1650
    assert features.loc[1, "montant_credits_30j"] == 1000
    assert features.loc[1, "solde_min_90j"] == -800
    assert features.loc[1, "jours_depuis_derniere_transaction"] == 7


def test_solde_moyen_somme_les_comptes(features):
    # Compte 10 : moyenne de 800, -700 et -800 ; compte 11 : 200.
    assert features.loc[1, "solde_moyen_30j"] == pytest.approx(-700 / 3 + 200)


def test_passage_a_decouvert_compte_une_fois(features):
    assert features.loc[1, "nb_decouverts_90j"] == 1


def test_client_sans_transaction_recente(features):
    assert features.loc[2, "nb_transactions_30j"] == 0
    assert features.loc[2, "nb_transactions_90j"] == 1
    assert math.isnan(features.loc[2, "solde_moyen_30j"])
    assert math.isnan(features.loc[2, "ratio_debits_credits_30j"])


def test_credits_et_endettement(features):
    assert features.loc[1, "nb_credits_actifs"] == 1
    assert features.loc[1, "ratio_endettement"] == pytest.approx(0.2)
    assert features.loc[2, "ratio_endettement"] == 0


def test_retards_sur_douze_mois(features):
    assert features.loc[1, "nb_retards_paiement_12m"] == 1
    assert features.loc[1, "jours_retard_max_12m"] == 10
    assert features.loc[2, "jours_retard_max_12m"] == 5


def test_contacts_sur_90_jours(features):
    assert features.loc[2, "nb_contacts_marketing_90j"] == 1
    assert features.loc[1, "nb_contacts_marketing_90j"] == 0


def test_instantane_anterieur_ignore_les_evenements_suivants(tables):
    avant = compute_features(tables, "2025-12-16").set_index("client_id")
    assert avant.loc[1, "nb_transactions_30j"] == 2
    assert avant.loc[1, "nb_decouverts_90j"] == 0


def test_build_features_concatene_les_instantanes():
    resultat = build_features(_tables_brutes(), ["2025-12-16", AS_OF])
    assert sorted(resultat["event_timestamp"].astype(str).unique()) == ["2025-12-16", AS_OF]
    assert len(resultat) == 4
