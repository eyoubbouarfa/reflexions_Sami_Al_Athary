"""Applique les validations de Sami : refait le PDF des cours validés (ou dévalidés) avec ou sans tampon.

Lancé par .github/workflows/tamponner.yml. Lit les validations sur le serveur, compare avec data/validations.json,
et écrit dans /tmp/a_refaire.txt les cours dont le PDF doit être refait.
"""
import json
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
API = json.loads((RACINE / "data" / "api.json").read_text())["url"]
FICHIER = RACINE / "data" / "validations.json"

with urllib.request.urlopen(urllib.request.Request(API + "/validations", headers={"User-Agent": "robot-reflexions"}), timeout=60) as r:
    serveur = json.loads(r.read())["validations"]
local = json.loads(FICHIER.read_text(encoding="utf-8")) if FICHIER.exists() else {}
pdfs = set(json.loads((RACINE / "data" / "pdfs.json").read_text()))
changes = [i for i in set(serveur) | set(local) if serveur.get(i) != local.get(i) and int(i) in pdfs]
FICHIER.write_text(json.dumps({k: serveur[k] for k in sorted(serveur, key=int)}, ensure_ascii=False, indent=0), encoding="utf-8")
Path("/tmp/a_refaire.txt").write_text(" ".join(sorted(changes, key=int)))
print("PDF à refaire :", " ".join(changes) or "aucun")
