"""Rattrapage Telegram : republie sur le canal les cours enregistrés dans l'appli qui n'y sont pas encore
(par exemple parce que le robot n'était pas encore administrateur du canal). Cours des 14 derniers jours.
Sans alerte : la première tentative en a déjà envoyé une. Lancé par .github/workflows/recevoir.yml."""
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
RACINE = Path(__file__).resolve().parent.parent
FICHIER = RACINE / "data" / "episodes.json"
CANAL = "Sami_Athary"


def main():
    jeton = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not jeton:
        return
    limite = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
    eps = json.loads(FICHIER.read_text(encoding="utf-8"))
    a_faire = [e for e in eps if e.get("source") == "appli" and "t.me/" not in (e.get("post") or "") and (e.get("date") or "") >= limite]
    change = False
    for e in a_faire:
        nom = e["audio"].rsplit("/", 1)[-1]
        if subprocess.run(["gh", "release", "download", "cours", "-p", nom, "-D", "/tmp", "--clobber"]).returncode:
            continue
        titre = (f"{e['num']} " if e.get("num") is not None else "") + (e.get("titre") or "Cours")
        r = subprocess.run(["curl", "-sS", "-m", "600", "-F", f"chat_id=@{CANAL}", "-F", f"caption={titre}", "-F", f"title={titre}",
                            "-F", "performer=Sami al Athary", "-F", f"audio=@/tmp/{nom}",
                            f"https://api.telegram.org/bot{jeton}/sendAudio"], capture_output=True, text=True)
        try:
            j = json.loads(r.stdout or "{}")
        except ValueError:
            j = {}
        if j.get("ok"):
            e["post"] = f"https://t.me/{CANAL}/{j['result']['message_id']}"
            change = True
            print("Publié sur Telegram :", titre)
        else:
            print("Pas encore possible :", titre, "-", j.get("description", "réponse vide"))
    if change:
        FICHIER.write_text(json.dumps(eps, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
