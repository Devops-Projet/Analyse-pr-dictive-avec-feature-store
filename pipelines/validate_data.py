"""Contrôle la qualité des données brutes et arrête le pipeline en cas d'erreur."""

import json
import sys
from pathlib import Path

import pandas as pd
import yaml

RAW_DIR = Path("data/raw")
REPORT_PATH = Path("data/interim/validation_report.json")

SCHEMA = {
    "clients": {
        "cle": "client_id",
        "dates": ["date_naissance", "date_entree"],
        "colonnes": [
            "revenu_mensuel",
            "utilise_app_mobile",
            "nb_produits",
            "defaut",
            "souscription",
        ],
    },
    "comptes": {"cle": "compte_id", "dates": ["date_ouverture"], "colonnes": ["client_id"]},
    "transactions": {
        "cle": "transaction_id",
        "dates": ["date_transaction"],
        "colonnes": ["compte_id", "montant", "solde_apres"],
    },
    "credits": {
        "cle": "credit_id",
        "dates": ["date_debut"],
        "colonnes": ["client_id", "mensualite"],
    },
    "retards": {"cle": None, "dates": ["date_echeance"], "colonnes": ["client_id", "jours_retard"]},
    "contacts": {"cle": None, "dates": ["date_contact"], "colonnes": ["client_id"]},
}

REFERENCES = [
    ("comptes", "client_id", "clients"),
    ("transactions", "compte_id", "comptes"),
    ("credits", "client_id", "clients"),
    ("retards", "client_id", "clients"),
    ("contacts", "client_id", "clients"),
]


def _valider_table(nom: str, table: pd.DataFrame, reference: pd.Timestamp) -> list[str]:
    schema = SCHEMA[nom]
    cle = [schema["cle"]] if schema["cle"] else []
    attendues = cle + schema["dates"] + schema["colonnes"]

    manquantes = [c for c in attendues if c not in table.columns]
    if manquantes:
        return [f"{nom} : colonnes manquantes {manquantes}"]

    erreurs = []
    if table.empty:
        erreurs.append(f"{nom} : table vide")
    nb_nuls = int(table[attendues].isna().sum().sum())
    if nb_nuls:
        erreurs.append(f"{nom} : {nb_nuls} valeurs manquantes")
    if cle and table[cle[0]].duplicated().any():
        erreurs.append(f"{nom} : doublons sur {cle[0]}")
    for colonne in schema["dates"]:
        dates = pd.to_datetime(table[colonne], errors="coerce")
        if dates.isna().sum() > table[colonne].isna().sum():
            erreurs.append(f"{nom} : dates invalides dans {colonne}")
        if (dates >= reference).any():
            erreurs.append(f"{nom} : {colonne} postérieure à la date de référence")
    return erreurs


def _valider_valeurs(tables: dict[str, pd.DataFrame]) -> list[str]:
    erreurs = []
    clients = tables["clients"]
    if (clients["revenu_mensuel"] <= 0).any():
        erreurs.append("clients : revenu_mensuel doit être positif")
    if (clients["nb_produits"] < 1).any():
        erreurs.append("clients : nb_produits doit valoir au moins 1")
    for cible in ("defaut", "souscription"):
        if not clients[cible].isin([0, 1]).all():
            erreurs.append(f"clients : {cible} doit valoir 0 ou 1")
        elif clients[cible].nunique() < 2:
            erreurs.append(f"clients : {cible} ne contient qu'une seule classe")
    if (tables["credits"]["mensualite"] <= 0).any():
        erreurs.append("credits : mensualite doit être positive")
    if (tables["retards"]["jours_retard"] <= 0).any():
        erreurs.append("retards : jours_retard doit être positif")
    return erreurs


def validate(tables: dict[str, pd.DataFrame], date_reference: str) -> list[str]:
    reference = pd.Timestamp(date_reference)
    erreurs = []
    for nom in SCHEMA:
        if nom not in tables:
            erreurs.append(f"{nom} : table absente")
        else:
            erreurs += _valider_table(nom, tables[nom], reference)
    if erreurs:
        return erreurs

    for nom, colonne, parent in REFERENCES:
        if not tables[nom][colonne].isin(tables[parent][colonne]).all():
            erreurs.append(f"{nom} : {colonne} inconnu dans {parent}")
    return erreurs + _valider_valeurs(tables)


def main() -> None:
    params = yaml.safe_load(Path("params.yaml").read_text(encoding="utf-8"))
    tables = {f.stem: pd.read_csv(f) for f in sorted(RAW_DIR.glob("*.csv"))}
    erreurs = validate(tables, params["data"]["date_reference"])

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rapport = {
        "valide": not erreurs,
        "erreurs": erreurs,
        "lignes": {nom: len(table) for nom, table in tables.items()},
    }
    REPORT_PATH.write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    if erreurs:
        print("\n".join(erreurs), file=sys.stderr)
        sys.exit(1)
    print(f"Données valides : {rapport['lignes']}")


if __name__ == "__main__":
    main()
