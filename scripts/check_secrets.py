"""Échoue si detect-secrets trouve un secret dans les fichiers suivis par Git.

Un faux positif se marque sur sa ligne avec le commentaire `# pragma: allowlist secret`.
"""

import json
import subprocess
import sys

files = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
scan = subprocess.run(
    [sys.executable, "-m", "detect_secrets", "scan", *files.stdout.split()],
    capture_output=True,
    text=True,
    check=True,
)
results = json.loads(scan.stdout)["results"]
for path, findings in results.items():
    for finding in findings:
        print(f"{path}:{finding['line_number']} : {finding['type']}")
if results:
    print("Secret potentiel détecté : le retirer du dépôt (et de l'historique) ou le marquer.")
    sys.exit(1)
print(f"Aucun secret détecté dans {len(files.stdout.split())} fichiers")
