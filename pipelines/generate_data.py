"""Génère les données bancaires synthétiques à partir d'une seed fixe."""

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAW_DIR = Path("data/raw")


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))


def _dates_avant(reference: pd.Timestamp, jours: np.ndarray) -> pd.Series:
    return pd.Series(reference - pd.to_timedelta(jours, unit="D"))


def _generer_clients(
    rng: np.random.Generator, n: int, reference: pd.Timestamp
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    # Facteurs cachés : ils relient les comportements aux cibles sans être publiés.
    risque = rng.normal(size=n)
    appetence = rng.normal(size=n)

    clients = pd.DataFrame(
        {
            "client_id": np.arange(1, n + 1),
            "date_naissance": _dates_avant(reference, rng.integers(18, 80, n) * 365),
            "date_entree": _dates_avant(reference, rng.integers(13, 240, n) * 30),
            "revenu_mensuel": np.round(rng.lognormal(7.8 - 0.2 * risque, 0.4), 2),
            "utilise_app_mobile": rng.random(n) < _sigmoid(0.5 + appetence),
            "nb_produits": 1 + rng.poisson(np.exp(0.4 * appetence)),
            "defaut": (rng.random(n) < _sigmoid(-2.2 + 1.2 * risque)).astype(int),
            "souscription": (rng.random(n) < _sigmoid(-1.2 + 1.3 * appetence)).astype(int),
        }
    )
    return clients, risque, appetence


def _generer_comptes(rng: np.random.Generator, clients: pd.DataFrame) -> pd.DataFrame:
    client_ids = np.repeat(clients["client_id"].to_numpy(), rng.integers(1, 4, len(clients)))
    comptes = pd.DataFrame(
        {"compte_id": np.arange(1, len(client_ids) + 1), "client_id": client_ids}
    )
    return comptes.merge(clients[["client_id", "date_entree"]]).rename(
        columns={"date_entree": "date_ouverture"}
    )


def _generer_transactions(
    rng: np.random.Generator,
    clients: pd.DataFrame,
    comptes: pd.DataFrame,
    risque: np.ndarray,
    reference: pd.Timestamp,
    historique_jours: int,
    transactions_par_mois: int,
) -> pd.DataFrame:
    position = comptes["client_id"].to_numpy() - 1
    revenus = clients["revenu_mensuel"].to_numpy()[position]
    risques = risque[position]

    moyenne = transactions_par_mois * historique_jours / 30
    nb = rng.poisson(moyenne, len(comptes))
    index = np.repeat(np.arange(len(comptes)), nb)
    total = len(index)

    # Les clients risqués dépensent davantage qu'ils ne reçoivent.
    part_credits = 0.25
    credit = rng.random(total) < part_credits
    taille_credit = revenus[index] * 12 / (transactions_par_mois * 12 * part_credits)
    taille_debit = (
        taille_credit
        * part_credits
        / (1 - part_credits)
        * np.clip(1 + 0.08 * risques[index], 0.7, 1.3)
    )
    montants = np.where(credit, taille_credit, -taille_debit) * rng.lognormal(0, 0.5, total)

    transactions = pd.DataFrame(
        {
            "compte_id": comptes["compte_id"].to_numpy()[index],
            "date_transaction": _dates_avant(
                reference, rng.integers(1, historique_jours + 1, total)
            ),
            "montant": np.round(montants, 2),
        }
    ).sort_values(["compte_id", "date_transaction"], kind="stable", ignore_index=True)

    soldes_initiaux = pd.Series(
        np.round(revenus * rng.lognormal(0, 0.5, len(comptes)), 2),
        index=comptes["compte_id"].to_numpy(),
    )
    transactions["solde_apres"] = np.round(
        transactions["compte_id"].map(soldes_initiaux)
        + transactions.groupby("compte_id")["montant"].cumsum(),
        2,
    )
    transactions.insert(0, "transaction_id", np.arange(1, total + 1))
    return transactions


def _generer_credits(
    rng: np.random.Generator,
    clients: pd.DataFrame,
    risque: np.ndarray,
    reference: pd.Timestamp,
) -> pd.DataFrame:
    position = np.repeat(np.arange(len(clients)), rng.poisson(np.exp(-0.3 + 0.3 * risque)))
    mensualites = clients["revenu_mensuel"].to_numpy()[position] * rng.uniform(
        0.05, 0.25, len(position)
    )
    return pd.DataFrame(
        {
            "credit_id": np.arange(1, len(position) + 1),
            "client_id": clients["client_id"].to_numpy()[position],
            "date_debut": _dates_avant(reference, rng.integers(30, 1500, len(position))).to_numpy(),
            "mensualite": np.round(mensualites, 2),
        }
    )


def _generer_retards(
    rng: np.random.Generator,
    clients: pd.DataFrame,
    risque: np.ndarray,
    reference: pd.Timestamp,
    historique_jours: int,
) -> pd.DataFrame:
    position = np.repeat(np.arange(len(clients)), rng.poisson(np.exp(-0.5 + 0.8 * risque)))
    return pd.DataFrame(
        {
            "client_id": clients["client_id"].to_numpy()[position],
            "date_echeance": _dates_avant(
                reference, rng.integers(1, historique_jours + 1, len(position))
            ).to_numpy(),
            "jours_retard": rng.integers(1, 90, len(position)),
        }
    )


def _generer_contacts(
    rng: np.random.Generator,
    clients: pd.DataFrame,
    appetence: np.ndarray,
    reference: pd.Timestamp,
    historique_jours: int,
) -> pd.DataFrame:
    position = np.repeat(np.arange(len(clients)), rng.poisson(np.exp(0.8 + 0.3 * appetence)))
    return pd.DataFrame(
        {
            "client_id": clients["client_id"].to_numpy()[position],
            "date_contact": _dates_avant(
                reference, rng.integers(1, historique_jours + 1, len(position))
            ).to_numpy(),
        }
    )


def generate(seed: int, config: dict) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    reference = pd.Timestamp(config["date_reference"])
    historique = config["historique_jours"]

    clients, risque, appetence = _generer_clients(rng, config["n_clients"], reference)
    comptes = _generer_comptes(rng, clients)
    return {
        "clients": clients,
        "comptes": comptes,
        "transactions": _generer_transactions(
            rng, clients, comptes, risque, reference, historique, config["transactions_par_mois"]
        ),
        "credits": _generer_credits(rng, clients, risque, reference),
        "retards": _generer_retards(rng, clients, risque, reference, historique),
        "contacts": _generer_contacts(rng, clients, appetence, reference, historique),
    }


def main() -> None:
    params = yaml.safe_load(Path("params.yaml").read_text(encoding="utf-8"))
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for nom, table in generate(params["seed"], params["data"]).items():
        table.to_csv(RAW_DIR / f"{nom}.csv", index=False, date_format="%Y-%m-%d")
        print(f"{nom}: {len(table)} lignes")


if __name__ == "__main__":
    main()
