# Catalogue des variables

Définitions de référence des variables du feature store. Le code source de vérité est
`feature_store/registry.py` (noms, types, consommateurs) et `feature_store/transformations.py`
(règles de calcul).

## Principes de calcul

- **Instantanés :** les variables sont calculées à chaque date de `features.snapshots`
  (`params.yaml`). Cette date devient l'`event_timestamp` de la valeur.
- **Pas de fuite :** une fenêtre de N jours couvre `[event_timestamp - N jours, event_timestamp[`.
  La date de calcul elle-même et tout ce qui la suit sont exclus.
- **Clients pris en compte :** seuls les clients entrés avant la date de calcul.
- **Valeurs manquantes :** les comptages valent 0 en l'absence d'événement. Les soldes, le ratio
  débits/crédits et l'inactivité restent vides quand aucune transaction ne permet de les calculer.
- **Version :** chaque chargement est enregistré sous `v-<12 premiers caractères du md5>` du
  fichier `data/features/features.csv`, c'est-à-dire l'empreinte notée par DVC.

## Variables

Consommateurs : S = scoring crédit, M = propension marketing.

| Variable | Type | Règle de calcul | Conso. |
|---|---|---|---|
| `age` | int | Années pleines entre la date de naissance et la date de calcul | S, M |
| `anciennete_mois` | int | Mois pleins depuis l'entrée du client | S, M |
| `revenu_mensuel` | float | Revenu mensuel déclaré | S, M |
| `solde_moyen_30j` | float | Moyenne des soldes après transaction par compte sur 30 jours, sommée sur les comptes | S, M |
| `solde_moyen_90j` | float | Même calcul sur 90 jours | S, M |
| `solde_min_90j` | float | Plus petit solde après transaction sur 90 jours, tous comptes confondus | S |
| `nb_transactions_30j` | int | Nombre de transactions sur 30 jours | S, M |
| `nb_transactions_90j` | int | Nombre de transactions sur 90 jours | M |
| `montant_debits_30j` | float | Somme des débits, en valeur positive, sur 30 jours | S, M |
| `montant_credits_30j` | float | Somme des crédits sur 30 jours | S, M |
| `ratio_debits_credits_30j` | float | `montant_debits_30j / montant_credits_30j`, vide si aucun crédit | S |
| `ratio_endettement` | float | Somme des mensualités des crédits commencés avant la date, divisée par le revenu | S |
| `nb_credits_actifs` | int | Nombre de crédits commencés avant la date | S |
| `nb_retards_paiement_12m` | int | Nombre d'échéances en retard sur 365 jours | S |
| `jours_retard_max_12m` | int | Plus long retard sur 365 jours, 0 sans retard | S |
| `nb_decouverts_90j` | int | Passages d'un solde positif ou nul à un solde négatif sur 90 jours | S |
| `nb_produits_detenus` | int | Nombre de produits détenus | M |
| `utilise_app_mobile` | bool | 1 si le client utilise l'application mobile, sinon 0 | M |
| `jours_depuis_derniere_transaction` | int | Jours entre la dernière transaction et la date de calcul | M |
| `nb_contacts_marketing_90j` | int | Nombre de sollicitations marketing sur 90 jours | M |

## Limites connues

`revenu_mensuel`, `nb_produits_detenus` et `utilise_app_mobile` sont des attributs actuels du
client : les données synthétiques n'en gardent pas l'historique, donc ils ont la même valeur à
chaque instantané.
