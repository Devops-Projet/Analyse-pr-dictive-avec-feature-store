"""Ajoute à .env les variables présentes dans .env.example mais absentes de .env.

Les valeurs existantes ne sont jamais modifiées. Usage : python3 scripts/sync_env.py
"""

import sys
from pathlib import Path


def missing_lines(example: str, current: str) -> list[str]:
    defined = {line.split("=", 1)[0] for line in current.splitlines() if "=" in line}
    return [
        line
        for line in example.splitlines()
        if "=" in line and not line.startswith("#") and line.split("=", 1)[0] not in defined
    ]


def main(example_path: str = ".env.example", env_path: str = ".env") -> None:
    env = Path(env_path)
    current = env.read_text(encoding="utf-8")
    added = missing_lines(Path(example_path).read_text(encoding="utf-8"), current)
    if added:
        separator = "" if current.endswith("\n") or not current else "\n"
        env.write_text(current + separator + "\n".join(added) + "\n", encoding="utf-8")
        for line in added:
            print(f"Ajout de {line.split('=', 1)[0]} dans {env_path} (valeur de {example_path})")


if __name__ == "__main__":
    main(*sys.argv[1:])
