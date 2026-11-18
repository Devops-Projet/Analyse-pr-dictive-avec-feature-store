"""Dessine docs/architecture.png : composants de la plateforme et flux entre eux.

Usage : docker compose run --rm --no-deps pipeline python scripts/draw_architecture.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUTPUT = Path("docs/architecture.png")

INK = "#1f2933"
MUTED = "#52606d"
COLORS = {
    "github": ("#e8eaf6", "#3949ab"),
    "pipeline": ("#e3f2fd", "#1565c0"),
    "store": ("#e8f5e9", "#2e7d32"),
    "mlflow": ("#fff3e0", "#ef6c00"),
    "api": ("#f3e5f5", "#7b1fa2"),
    "monitoring": ("#fce4ec", "#c2185b"),
    "user": ("#eceff1", "#455a64"),
}


def box(ax, x, y, w, h, title, lines, kind):
    fill, edge = COLORS[kind]
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            facecolor=fill,
            edgecolor=edge,
            linewidth=1.6,
        )
    )
    ax.text(
        x + w / 2,
        y + h - 0.22,
        title,
        ha="center",
        va="top",
        fontsize=10.5,
        fontweight="bold",
        color=edge,
    )
    ax.text(
        x + w / 2,
        y + h - 0.58,
        "\n".join(lines),
        ha="center",
        va="top",
        fontsize=8.2,
        color=INK,
        linespacing=1.35,
    )


def arrow(ax, start, end, label="", both=False, offset=(0, 0.14), rad=0.0):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="<|-|>" if both else "-|>",
            mutation_scale=13,
            color=MUTED,
            linewidth=1.3,
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=2,
            shrinkB=2,
        )
    )
    if label:
        mx = (start[0] + end[0]) / 2 + offset[0]
        my = (start[1] + end[1]) / 2 + offset[1]
        ax.text(
            mx,
            my,
            label,
            ha="center",
            va="bottom",
            fontsize=7.6,
            color=MUTED,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0},
        )


def main() -> None:
    fig, ax = plt.subplots(figsize=(16, 9.4))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9.4)
    ax.axis("off")

    ax.text(
        0.3,
        9.15,
        "Architecture de la plateforme de feature store",
        fontsize=15,
        fontweight="bold",
        color=INK,
        va="top",
    )

    # Livraison : GitHub et intégration continue
    box(
        ax,
        0.6,
        6.95,
        4.2,
        1.45,
        "Git / GitHub",
        ["Une branche par tâche, pull request", "relue par l'autre développeur"],
        "github",
    )
    box(
        ax,
        5.9,
        6.95,
        4.2,
        1.45,
        "GitHub Actions (CI)",
        ["Lint, secrets, tests sur PostgreSQL,", "validation des modèles, build des images"],
        "github",
    )
    box(
        ax,
        11.2,
        6.95,
        4.2,
        1.45,
        "Images Docker",
        ["api et pipeline,", "étiquetées avec le hash du commit"],
        "github",
    )
    arrow(ax, (4.8, 7.67), (5.9, 7.67), "push / PR")
    arrow(ax, (10.1, 7.67), (11.2, 7.67), "build")

    # Environnement d'exécution
    ax.add_patch(
        FancyBboxPatch(
            (0.3, 0.3),
            15.4,
            6.2,
            boxstyle="round,pad=0.02,rounding_size=0.2",
            facecolor="none",
            edgecolor="#9aa5b1",
            linewidth=1.2,
            linestyle="--",
        )
    )
    ax.text(
        0.55,
        6.32,
        "Docker Compose · lancé par  make all",
        fontsize=9.5,
        color=MUTED,
        va="top",
        style="italic",
    )
    arrow(ax, (13.3, 6.95), (13.3, 6.5), "")

    box(
        ax,
        0.6,
        3.75,
        4.2,
        2.15,
        "Pipeline DVC",
        [
            "generate → validate → build_features",
            "→ load_features → drift",
            "→ train_scoring / train_marketing",
            "→ evaluate (règle de promotion)",
        ],
        "pipeline",
    )
    box(
        ax,
        0.6,
        0.65,
        4.2,
        2.15,
        "Fichiers suivis par DVC",
        [
            "data/ : données brutes et features.csv",
            "params.yaml, dvc.lock",
            "reports/ : métriques et dérive",
            "(version du store = md5 de features.csv)",
        ],
        "pipeline",
    )
    box(
        ax,
        6.0,
        3.75,
        3.6,
        2.15,
        "Feature store · PostgreSQL",
        [
            "20 variables, 2 consommateurs",
            "valeurs datées (point dans le temps)",
            "une version par jeu de variables",
        ],
        "store",
    )
    box(
        ax,
        6.0,
        0.65,
        3.6,
        2.15,
        "MLflow",
        [
            "Suivi des entraînements",
            "Registre des modèles :",
            "alias production / previous",
            "(retour arrière sans redémarrage)",
        ],
        "mlflow",
    )
    box(
        ax,
        10.8,
        2.3,
        2.6,
        2.6,
        "API FastAPI",
        [
            "/features/{client_id}",
            "/features/batch",
            "/predict/scoring",
            "/predict/marketing",
            "/health  /ready  /metrics",
        ],
        "api",
    )
    box(
        ax,
        13.75,
        4.25,
        1.75,
        1.65,
        "Utilisateurs",
        ["Équipes risque", "et marketing,", "make smoke"],
        "user",
    )
    box(
        ax,
        10.8,
        0.65,
        2.6,
        1.15,
        "Prometheus",
        ["collecte /metrics", "5 règles d'alerte"],
        "monitoring",
    )
    box(ax, 13.75, 0.65, 1.75, 1.15, "Grafana", ["tableau de bord"], "monitoring")

    arrow(ax, (2.7, 3.75), (2.7, 2.8), "dvc repro", both=True, offset=(0.55, -0.12))
    arrow(ax, (4.8, 5.15), (6.0, 5.15), "charge les variables", offset=(0, 0.1))
    arrow(ax, (6.0, 4.45), (4.8, 4.45), "jeux d'entraînement", offset=(0, 0.1))
    arrow(ax, (4.8, 3.95), (6.0, 2.3), "entraîne, enregistre,\npromeut", offset=(0.25, -0.2))
    arrow(ax, (9.6, 4.6), (10.8, 4.2), "variables", offset=(0, 0.12))
    arrow(ax, (9.6, 1.9), (10.8, 2.8), "modèle en\nproduction", offset=(-0.15, 0.05))
    arrow(ax, (13.75, 4.9), (13.4, 4.4), "", both=True)
    ax.text(13.9, 4.0, "HTTP", fontsize=7.6, color=MUTED)
    arrow(ax, (12.1, 1.8), (12.1, 2.3), "")
    ax.text(12.2, 1.95, "scrape", fontsize=7.6, color=MUTED)
    arrow(ax, (13.4, 1.22), (13.75, 1.22), "")

    OUTPUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"Schéma écrit dans {OUTPUT}")


if __name__ == "__main__":
    main()
