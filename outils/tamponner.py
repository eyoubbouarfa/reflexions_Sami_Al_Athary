"""Applique les décisions de Sami sur les PDF (lancé par .github/workflows/tamponner.yml).

Statuts tenus par le serveur : validé (PDF tamponné), retiré (PDF retiré de l'appli), ou rien (non relu).
Compare avec data/validations.json et écrit :
  /tmp/a_refaire.txt  : cours dont le PDF doit être refait (tampon ajouté ou enlevé, retour d'un PDF retiré)
  /tmp/a_retirer.txt  : cours dont le PDF doit être retiré
Option : python outils/tamponner.py --refaire "1823 1820" ou --refaire tous (refait aussi ces PDF).
"""
import json
import sys
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
API = json.loads((RACINE / "data" / "api.json").read_text())["url"]
FICHIER = RACINE / "data" / "validations.json"

with urllib.request.urlopen(urllib.request.Request(API + "/validations", headers={"User-Agent": "robot-reflexions"}), timeout=60) as r:
    serveur = json.loads(r.read())["validations"]
local = json.loads(FICHIER.read_text(encoding="utf-8")) if FICHIER.exists() else {}
pdfs = set(json.loads((RACINE / "data" / "pdfs.json").read_text()))
retire = lambda v: bool(v) and v.get("statut") == "retire"  # noqa: E731

refaire, retirer = set(), set()
for i in set(serveur) | set(local):
    avant, apres = local.get(i), serveur.get(i)
    if avant == apres:
        continue
    if retire(apres):
        retirer.add(i)
    elif retire(avant) or int(i) in pdfs:
        refaire.add(i)

if "--refaire" in sys.argv:
    demande = sys.argv[sys.argv.index("--refaire") + 1].split()
    refaire |= {str(i) for i in pdfs} if demande == ["tous"] else set(demande)
    refaire -= {i for i, v in serveur.items() if retire(v)}

FICHIER.write_text(json.dumps({k: serveur[k] for k in sorted(serveur, key=int)}, ensure_ascii=False, indent=0), encoding="utf-8")
Path("/tmp/a_refaire.txt").write_text(" ".join(sorted(refaire, key=int)))
Path("/tmp/a_retirer.txt").write_text(" ".join(sorted(retirer, key=int)))
print("PDF à refaire :", len(refaire), "| PDF à retirer :", " ".join(sorted(retirer)) or "aucun")
