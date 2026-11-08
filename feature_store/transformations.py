"""Calcul des variables à une date donnée, sans utiliser de données postérieures."""

import numpy as np
import pandas as pd

from feature_store.registry import FEATURE_NAMES

DATE_COLUMNS = {
    "clients": ["date_naissance", "date_entree"],
    "transactions": ["date_transaction"],
    "credits": ["date_debut"],
    "retards": ["date_echeance"],
    "contacts": ["date_contact"],
}


def parse_dates(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    parsed = {}
    for nom, table in tables.items():
        table = table.copy()
        for colonne in DATE_COLUMNS.get(nom, []):
            table[colonne] = pd.to_datetime(table[colonne])
        parsed[nom] = table
    return parsed


def _fenetre(table: pd.DataFrame, colonne: str, as_of: pd.Timestamp, jours: int) -> pd.DataFrame:
    """Lignes dans [as_of - jours, as_of[ : la date de calcul elle-même est exclue."""
    debut = as_of - pd.Timedelta(days=jours)
    return table[(table[colonne] >= debut) & (table[colonne] < as_of)]


def _mois_ecoules(debut: pd.Series, as_of: pd.Timestamp) -> pd.Series:
    mois = (as_of.year - debut.dt.year) * 12 + (as_of.month - debut.dt.month)
    return mois - (as_of.day < debut.dt.day)


def _variables_transactions(
    transactions: pd.DataFrame, as_of: pd.Timestamp
) -> dict[str, pd.Series]:
    passees = transactions[transactions["date_transaction"] < as_of].sort_values(
        ["compte_id", "date_transaction"], kind="stable"
    )
    precedent = passees.groupby("compte_id")["solde_apres"].shift()
    passees = passees.assign(
        passage_decouvert=(passees["solde_apres"] < 0) & ~(precedent < 0),
        debit=-passees["montant"].clip(upper=0),
        credit=passees["montant"].clip(lower=0),
    )
    t30 = _fenetre(passees, "date_transaction", as_of, 30)
    t90 = _fenetre(passees, "date_transaction", as_of, 90)

    def solde_moyen(fenetre: pd.DataFrame) -> pd.Series:
        # Moyenne par compte, puis somme des comptes du client.
        par_compte = fenetre.groupby(["client_id", "compte_id"])["solde_apres"].mean()
        return par_compte.groupby("client_id").sum()

    debits = t30.groupby("client_id")["debit"].sum()
    credits = t30.groupby("client_id")["credit"].sum()
    return {
        "solde_moyen_30j": solde_moyen(t30),
        "solde_moyen_90j": solde_moyen(t90),
        "solde_min_90j": t90.groupby("client_id")["solde_apres"].min(),
        "nb_transactions_30j": t30.groupby("client_id").size(),
        "nb_transactions_90j": t90.groupby("client_id").size(),
        "montant_debits_30j": debits,
        "montant_credits_30j": credits,
        "ratio_debits_credits_30j": debits / credits.replace(0, np.nan),
        "nb_decouverts_90j": t90.groupby("client_id")["passage_decouvert"].sum(),
        "jours_depuis_derniere_transaction": (
            as_of - passees.groupby("client_id")["date_transaction"].max()
        ).dt.days,
    }


# Variables de comptage : un client sans événement vaut 0, pas « inconnu ».
COMPTAGES = [
    "nb_transactions_30j",
    "nb_transactions_90j",
    "montant_debits_30j",
    "montant_credits_30j",
    "nb_credits_actifs",
    "nb_retards_paiement_12m",
    "jours_retard_max_12m",
    "nb_decouverts_90j",
    "nb_contacts_marketing_90j",
]


def compute_features(tables: dict[str, pd.DataFrame], as_of: str | pd.Timestamp) -> pd.DataFrame:
    """Variables de chaque client déjà présent à `as_of`, calculées sur le passé seul."""
    as_of = pd.Timestamp(as_of)
    clients = tables["clients"]
    clients = clients[clients["date_entree"] < as_of].set_index("client_id")
    transactions = tables["transactions"].merge(tables["comptes"][["compte_id", "client_id"]])

    credits = tables["credits"][tables["credits"]["date_debut"] < as_of]
    retards = _fenetre(tables["retards"], "date_echeance", as_of, 365)
    contacts = _fenetre(tables["contacts"], "date_contact", as_of, 90)
    mensualites = credits.groupby("client_id")["mensualite"].sum()

    colonnes = {
        "age": ((as_of - clients["date_naissance"]).dt.days // 365.25).astype(int),
        "anciennete_mois": _mois_ecoules(clients["date_entree"], as_of),
        "revenu_mensuel": clients["revenu_mensuel"],
        **_variables_transactions(transactions, as_of),
        "ratio_endettement": mensualites.reindex(clients.index, fill_value=0)
        / clients["revenu_mensuel"],
        "nb_credits_actifs": credits.groupby("client_id").size(),
        "nb_retards_paiement_12m": retards.groupby("client_id").size(),
        "jours_retard_max_12m": retards.groupby("client_id")["jours_retard"].max(),
        "nb_produits_detenus": clients["nb_produits"],
        "utilise_app_mobile": clients["utilise_app_mobile"].astype(int),
        "nb_contacts_marketing_90j": contacts.groupby("client_id").size(),
    }
    features = pd.DataFrame({nom: serie.reindex(clients.index) for nom, serie in colonnes.items()})
    features[COMPTAGES] = features[COMPTAGES].fillna(0)
    features = features.reset_index().assign(event_timestamp=as_of)
    return features[["client_id", "event_timestamp", *FEATURE_NAMES]]


def build_features(tables: dict[str, pd.DataFrame], snapshots: list[str]) -> pd.DataFrame:
    tables = parse_dates(tables)
    return pd.concat([compute_features(tables, date) for date in snapshots], ignore_index=True)
