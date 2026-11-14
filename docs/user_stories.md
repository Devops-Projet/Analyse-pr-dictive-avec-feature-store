# User stories et critères d'acceptation

Chaque incrément part d'un besoin vérifiable. Une story est terminée lorsque tous ses
critères sont couverts par un test automatisé ou par une vérification documentée.

## Définition de « terminé »

Une pull request est fusionnée dans `main` seulement si :

1. le code a été **relu et approuvé par l'autre développeur** ;
2. les tests (`make test`) et le lint (`make lint`) réussissent ;
3. les critères d'acceptation de la story sont couverts par des tests ;
4. la configuration nouvelle est documentée dans `.env.example` ou `params.yaml`, sans secret ;
5. le README et le catalogue sont à jour si le comportement visible change ;
6. les signaux de suivi (métriques, logs) sont prévus pour tout nouveau service.

## US1 — Lire les variables d'un client

> En tant que data scientist, je veux récupérer les variables d'un client depuis le store afin
> de ne pas les recalculer dans mon projet.

1. `GET /features/{client_id}` renvoie les 20 variables et la version du store utilisée.
2. Un client inconnu renvoie `404`, une variable inconnue `400`.
3. Avec `as_of`, seules des valeurs calculées à cette date ou avant sont renvoyées.

## US2 — Entraîner sans fuite de données

> En tant que data scientist, je veux construire un jeu d'entraînement au point dans le temps
> afin que mon modèle n'apprenne pas sur des informations futures.

1. Une variable calculée à une date n'utilise aucun événement postérieur à cette date.
2. La jointure historique associe à chaque ligne le dernier instantané antérieur.
3. Deux exécutions avec les mêmes paramètres produisent la même version du store.

## US3 — Évaluer le risque de défaut

> En tant qu'analyste crédit, je veux une probabilité de défaut pour un client afin de
> décider de l'octroi d'un crédit.

1. `POST /predict/scoring` renvoie une probabilité entre 0 et 1 et la version du modèle.
2. Le modèle lit ses variables uniquement depuis le store.
3. Un modèle n'est mis en production que si son AUC dépasse le seuil minimal et celle du
   modèle en production.

## US4 — Cibler une campagne marketing

> En tant que chargé de marketing, je veux la probabilité de souscription d'un client afin de
> cibler une campagne.

1. `POST /predict/marketing` renvoie une probabilité entre 0 et 1 et la version du modèle.
2. Le modèle marketing réutilise des variables partagées avec le modèle de scoring.
3. Les valeurs manquantes d'un client ne provoquent pas d'erreur.

## US5 — Revenir à la version précédente

> En tant que responsable de la livraison, je veux revenir au modèle précédent en une
> commande afin de rétablir le service si un nouveau modèle se dégrade.

1. `make rollback MODEL=<nom>` remet en production la version précédente.
2. L'API sert la version rétablie sans redémarrage.
3. La procédure est décrite dans `docs/runbook.md`.

## US6 — Reconstruire le projet depuis un clone

> En tant que nouveau membre de l'équipe, je veux tout reconstruire avec une seule commande
> afin de commencer à travailler sans étape manuelle cachée.

1. `make all` démarre les services, relance le pipeline et entraîne les modèles.
2. Il échoue avec un message clair si une variable de configuration manque.
3. Une seconde exécution ne recalcule rien qui n'a pas changé.
