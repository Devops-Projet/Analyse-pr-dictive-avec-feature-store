"""Indicateurs DORA mesurés sur l'historique Git de `main`.

Une livraison est une fusion de pull request dans `main` : chaque fusion déclenche la CI, qui
construit les images, et `make all` les déploie. Le script calcule :

- la fréquence de livraison (fusions par semaine active) ;
- le délai de mise en production (du commit à sa fusion dans `main`), en médiane.

Le taux d'échec des changements et le temps de rétablissement viennent du journal des incidents
(docs/dora.md), car un échec ne se lit pas dans l'historique Git.

Usage : python3 scripts/dora.py [branche]   (sans dépendance, à lancer hors conteneur)
"""

import statistics
import subprocess
import sys
from datetime import datetime


def git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def deliveries(branch: str) -> list[tuple[str, datetime, list[datetime]]]:
    """(hash, date de fusion, dates des commits apportés) pour chaque fusion dans `branch`."""
    result = []
    for line in git("log", "--first-parent", "--merges", "--format=%H %cI", branch):
        sha, merged = line.split()
        commits = git("log", "--format=%aI", f"{sha}^1..{sha}^2")
        result.append(
            (sha, datetime.fromisoformat(merged), [datetime.fromisoformat(c) for c in commits])
        )
    return sorted(result, key=lambda d: d[1])


def main() -> None:
    branch = sys.argv[1] if len(sys.argv) > 1 else "main"
    items = deliveries(branch)
    if not items:
        sys.exit(f"Aucune fusion trouvée sur {branch}")

    weeks = {d[1].isocalendar()[:2] for d in items}
    days = {d[1].date() for d in items}
    lead_hours = [(merged - c).total_seconds() / 3600 for _, merged, cs in items for c in cs]

    print(
        f"Livraisons sur {branch} : {len(items)} fusions, {len(days)} jours, {len(weeks)} semaines"
    )
    print(f"Fréquence de livraison : {len(items) / len(weeks):.1f} fusions par semaine active")
    print(
        f"Délai de mise en production : médiane {statistics.median(lead_hours):.1f} h, "
        f"maximum {max(lead_hours):.1f} h ({len(lead_hours)} commits)"
    )
    print()
    print("| Fusion | Date | Commits | Délai médian (h) |")
    print("|---|---|---|---|")
    for sha, merged, commits in items:
        median = statistics.median((merged - c).total_seconds() / 3600 for c in commits)
        print(f"| {sha[:7]} | {merged:%d/%m/%Y %H:%M} | {len(commits)} | {median:.1f} |")


if __name__ == "__main__":
    main()
