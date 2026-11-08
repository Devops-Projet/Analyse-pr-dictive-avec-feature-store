"""Catalogue des définitions de variables du store."""

from dataclasses import dataclass

from sqlalchemy import Connection, Engine, text

DTYPES = ("int", "float", "bool")
OWNER = "equipe-data"


@dataclass(frozen=True)
class FeatureDefinition:
    name: str
    dtype: str
    description: str
    consumers: tuple[str, ...]
    owner: str = OWNER
    version: int = 1


S, M = "scoring", "marketing"

FEATURES: tuple[FeatureDefinition, ...] = (
    FeatureDefinition("age", "int", "Âge du client en années", (S, M)),
    FeatureDefinition("anciennete_mois", "int", "Ancienneté de la relation bancaire", (S, M)),
    FeatureDefinition("revenu_mensuel", "float", "Revenu mensuel déclaré", (S, M)),
    FeatureDefinition("solde_moyen_30j", "float", "Solde moyen sur 30 jours", (S, M)),
    FeatureDefinition("solde_moyen_90j", "float", "Solde moyen sur 90 jours", (S, M)),
    FeatureDefinition("solde_min_90j", "float", "Solde minimal sur 90 jours", (S,)),
    FeatureDefinition("nb_transactions_30j", "int", "Nombre de transactions sur 30 jours", (S, M)),
    FeatureDefinition("nb_transactions_90j", "int", "Nombre de transactions sur 90 jours", (M,)),
    FeatureDefinition("montant_debits_30j", "float", "Total des débits sur 30 jours", (S, M)),
    FeatureDefinition("montant_credits_30j", "float", "Total des crédits sur 30 jours", (S, M)),
    FeatureDefinition(
        "ratio_debits_credits_30j", "float", "Débits divisés par crédits sur 30 jours", (S,)
    ),
    FeatureDefinition(
        "ratio_endettement", "float", "Mensualités de crédit divisées par le revenu", (S,)
    ),
    FeatureDefinition("nb_credits_actifs", "int", "Nombre de crédits en cours", (S,)),
    FeatureDefinition("nb_retards_paiement_12m", "int", "Retards de paiement sur 12 mois", (S,)),
    FeatureDefinition(
        "jours_retard_max_12m", "int", "Plus long retard de paiement sur 12 mois", (S,)
    ),
    FeatureDefinition("nb_decouverts_90j", "int", "Passages à découvert sur 90 jours", (S,)),
    FeatureDefinition("nb_produits_detenus", "int", "Nombre de produits détenus", (M,)),
    FeatureDefinition("utilise_app_mobile", "bool", "Utilisation de l'application mobile", (M,)),
    FeatureDefinition(
        "jours_depuis_derniere_transaction", "int", "Jours depuis la dernière transaction", (M,)
    ),
    FeatureDefinition(
        "nb_contacts_marketing_90j", "int", "Sollicitations marketing sur 90 jours", (M,)
    ),
)

FEATURE_NAMES: list[str] = [f.name for f in FEATURES]


def features_for(consumer: str) -> list[str]:
    """Variables utilisées par un modèle consommateur (`scoring` ou `marketing`)."""
    return [f.name for f in FEATURES if consumer in f.consumers]


def register_definitions(conn: Connection) -> None:
    conn.execute(
        text("""
            INSERT INTO feature_definitions (name, dtype, description, owner, version)
            VALUES (:name, :dtype, :description, :owner, :version)
            ON CONFLICT (name) DO UPDATE SET
                dtype = EXCLUDED.dtype,
                description = EXCLUDED.description,
                owner = EXCLUDED.owner,
                version = EXCLUDED.version,
                updated_at = now()
            """),
        [
            {
                "name": f.name,
                "dtype": f.dtype,
                "description": f.description,
                "owner": f.owner,
                "version": f.version,
            }
            for f in FEATURES
        ],
    )


def list_definitions(engine: Engine) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT name, dtype, description, owner, version "
                "FROM feature_definitions ORDER BY name"
            )
        )
        return [dict(row._mapping) for row in rows]
