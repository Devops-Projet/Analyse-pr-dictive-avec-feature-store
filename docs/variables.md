# Variables partagées

Liste initiale des variables du store. Les fenêtres de calcul seront paramétrées dans
`params.yaml`. Consommateurs : S = scoring crédit, M = propension marketing.

| # | Variable | Type | Description | Conso. |
|---|---|---|---|---|
| 1 | `age` | entier | Âge du client en années | S, M |
| 2 | `anciennete_mois` | entier | Ancienneté de la relation bancaire | S, M |
| 3 | `revenu_mensuel` | réel | Revenu mensuel déclaré | S, M |
| 4 | `solde_moyen_30j` | réel | Solde moyen sur 30 jours | S, M |
| 5 | `solde_moyen_90j` | réel | Solde moyen sur 90 jours | S, M |
| 6 | `solde_min_90j` | réel | Solde minimal sur 90 jours | S |
| 7 | `nb_transactions_30j` | entier | Nombre de transactions sur 30 jours | S, M |
| 8 | `nb_transactions_90j` | entier | Nombre de transactions sur 90 jours | M |
| 9 | `montant_debits_30j` | réel | Total des débits sur 30 jours | S, M |
| 10 | `montant_credits_30j` | réel | Total des crédits sur 30 jours | S, M |
| 11 | `ratio_debits_credits_30j` | réel | Débits divisés par crédits sur 30 jours | S |
| 12 | `ratio_endettement` | réel | Mensualités de crédit divisées par le revenu | S |
| 13 | `nb_credits_actifs` | entier | Nombre de crédits en cours | S |
| 14 | `nb_retards_paiement_12m` | entier | Retards de paiement sur 12 mois | S |
| 15 | `jours_retard_max_12m` | entier | Plus long retard de paiement sur 12 mois | S |
| 16 | `nb_decouverts_90j` | entier | Passages à découvert sur 90 jours | S |
| 17 | `nb_produits_detenus` | entier | Nombre de produits détenus | M |
| 18 | `utilise_app_mobile` | booléen | Utilisation de l'application mobile | M |
| 19 | `jours_depuis_derniere_transaction` | entier | Inactivité du client | M |
| 20 | `nb_contacts_marketing_90j` | entier | Sollicitations marketing sur 90 jours | M |

Chaque valeur est calculée à une date (`event_timestamp`) : seules les données antérieures
à cette date entrent dans le calcul, afin d'éviter les fuites à l'entraînement.
