"""Recalcule data/pdfs.json : les PDF réellement rangés, des cours existants, hors PDF retirés par Sami."""
import json
import subprocess
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
noms = subprocess.run(["gh", "release", "view", "cours", "--json", "assets", "-q", ".assets[].name"],
                      capture_output=True, text=True, check=True).stdout.split()
eps = {e["id"] for e in json.loads((RACINE / "data" / "episodes.json").read_text(encoding="utf-8"))}
val_f = RACINE / "data" / "validations.json"
retires = {int(i) for i, v in (json.loads(val_f.read_text(encoding="utf-8")) if val_f.exists() else {}).items() if v.get("statut") == "retire"}
pdfs = sorted(int(n[:-4]) for n in noms if n.endswith(".pdf") and n[:-4].isdigit() and int(n[:-4]) in eps and int(n[:-4]) not in retires)
(RACINE / "data" / "pdfs.json").write_text(json.dumps(pdfs), encoding="utf-8")
print(len(pdfs), "PDF dans l'appli")
