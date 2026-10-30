# Conventions de contribution

## Branches

- `main` reste stable : on n'y pousse pas directement.
- Chaque tâche a sa branche : `feature/<sujet>` (ou `fix/<sujet>`).

## Commits

Commits atomiques au format [Conventional Commits](https://www.conventionalcommits.org/fr/) :

```
feat(api): ajouter la récupération des variables par client
fix(store): corriger le filtre sur event_timestamp
docs: compléter le catalogue des variables
```

Types utilisés : `feat`, `fix`, `docs`, `test`, `chore`, `ci`, `refactor`.

## Pull requests

- Toute modification passe par une pull request vers `main`.
- La pull request est relue par l'autre développeur avant la fusion.

## Secrets et données

- Aucun secret dans Git : les valeurs restent dans `.env`, ignoré par Git.
- Aucun fichier volumineux dans Git : les données et artefacts sont suivis par DVC.
