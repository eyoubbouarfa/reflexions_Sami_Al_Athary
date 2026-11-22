"""Grave dans les données les corrections faites par Sami dans l'appli (titre, livre, numéro d'un cours, livres ajoutés).

Lancé toutes les heures par .github/workflows/tamponner.yml :
    python3 outils/corriger.py                     # lit les corrections sur le serveur et les applique
    python3 outils/corriger.py --fichier f.json    # applique des corrections déjà téléchargées
Écrit dans /tmp/corriges.txt les cours réellement modifiés (leur PDF est refait s'il existe).
Les corrections sont rejouées à chaque passage : les appliquer deux fois ne change rien.
"""
import json
import sys
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
EPISODES = RACINE / "data" / "episodes.json"
LIVRES = RACINE / "data" / "livres_ajoutes.json"


def lire_serveur():
    api = json.loads((RACINE / "data" / "api.json").read_text())["url"]
    req = urllib.request.Request(api + "/corrections", headers={"User-Agent": "robot-reflexions"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main():
    if "--fichier" in sys.argv:
        donnees = json.loads(Path(sys.argv[sys.argv.index("--fichier") + 1]).read_text(encoding="utf-8"))
    else:
        donnees = lire_serveur()
        Path("/tmp/corrections.json").write_text(json.dumps(donnees, ensure_ascii=False), encoding="utf-8")

    # 1. Livres ajoutés (avant d'importer series.py, qui les lit)
    anciens = json.loads(LIVRES.read_text(encoding="utf-8")) if LIVRES.exists() else []
    par_id = {l["id"]: l for l in anciens}
    for l in donnees.get("livres", []):
        par_id[l["id"]] = {k: l.get(k, "") for k in ("id", "nom", "auteur", "theme", "type", "statut", "date")}
    livres = sorted(par_id.values(), key=lambda l: l.get("date", ""))
    if livres != anciens:
        LIVRES.write_text(json.dumps(livres, ensure_ascii=False, indent=1), encoding="utf-8")

    sys.path.insert(0, str(Path(__file__).parent))
    from series import SERIES  # noqa: E402
    from synchro import maj_series  # noqa: E402
    connues = {s["id"] for s in SERIES}

    # 2. Cours corrigés
    eps = json.loads(EPISODES.read_text(encoding="utf-8"))
    par_ep = {str(e["id"]): e for e in eps}
    modifies = []
    for i, c in donnees.get("corrections", {}).items():
        e = par_ep.get(str(i))
        if not e or c.get("serie") not in connues:
            continue
        avant = (e.get("titre"), e.get("serie"), e.get("num"), bool(e.get("fin")))
        e.update(titre=c.get("titre", ""), serie=c["serie"], num=c.get("num"), fin=bool(c.get("fin")))
        if avant != (e["titre"], e["serie"], e["num"], e["fin"]):
            modifies.append(str(i))
    if modifies:
        EPISODES.write_text(json.dumps(eps, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if modifies or livres != anciens:
        maj_series(eps)
    Path("/tmp/corriges.txt").write_text(" ".join(modifies))
    print(f"Cours corrigés : {' '.join(modifies) or 'aucun'} | livres ajoutés : {len(livres)}")


if __name__ == "__main__":
    main()
