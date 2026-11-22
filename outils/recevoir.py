"""Range les cours enregistrés par Sami depuis l'appli.

Lancé toutes les 10 minutes par GitHub (.github/workflows/recevoir.yml).
1. Demande au serveur la liste des enregistrements terminés.
2. Télécharge les parties, les assemble et les convertit en mp3 (ffmpeg).
3. Dépose le mp3 dans la release GitHub « enregistrements » (stockage gratuit et durable).
4. Ajoute le cours à data/episodes.json, classé d'après son titre, puis le retire du serveur.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from import_telegram import decouper, serie_de  # noqa: E402
from series import SERIES  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
FICHIER = RACINE / "data" / "episodes.json"
API = json.loads((RACINE / "data" / "api.json").read_text())["url"]
CF = next(s for s in SERIES if s["code"] == "CF")
ETIQUETTE = "cours"
CANAL = "Sami_Athary"


def cle_robot():
    sig = hmac.new(os.environ["CODE_SAMI"].encode(), b"robot", hashlib.sha256).digest()
    return base64.b64encode(sig).decode().translate(str.maketrans("+/", "-_")).rstrip("=")


def appel(chemin, methode="GET", donnees=None):
    req = urllib.request.Request(API + chemin, method=methode, data=json.dumps(donnees).encode() if donnees else None,
                                 headers={"X-Robot": cle_robot(), "User-Agent": "robot-reflexions", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def alerte(texte):
    try:
        appel("/alertes", "POST", {"texte": texte})
    except Exception as e:
        print("Alerte non envoyée :", e)


def copie_telegram(fichier, titre, duree):
    """Publie le mp3 sur le canal avec le robot Telegram. Renvoie le lien du post, ou None (et alerte Sami)."""
    jeton = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not jeton:
        alerte(f"« {titre} » n'a pas été copié sur Telegram : le robot Telegram n'est pas encore réglé. Le cours est bien dans l'appli.")
        return None
    try:
        r = subprocess.run(["curl", "-sS", "-m", "600", "-F", f"chat_id=@{CANAL}", "-F", f"caption={titre}", "-F", f"title={titre}",
                            "-F", "performer=Sami al Athary", "-F", f"duration={duree}", "-F", f"audio=@{fichier}",
                            f"https://api.telegram.org/bot{jeton}/sendAudio"], capture_output=True, text=True, timeout=700)
        j = json.loads(r.stdout or "{}")
        if not j.get("ok"):
            raise RuntimeError(j.get("description") or (r.stderr or "").strip()[:200] or f"réponse vide, code {r.returncode}")
        return f"https://t.me/{CANAL}/{j['result']['message_id']}"
    except Exception as e:
        alerte(f"« {titre} » n'a pas pu être copié sur Telegram ({e}). Le cours est bien dans l'appli ; publie-le à la main si besoin.")
        return None


def duree_s(fichier):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(fichier)], capture_output=True, text=True)
    try:
        return int(float(r.stdout.strip()))
    except ValueError:
        return 0


def nom_fichier(c):
    t = unicodedata.normalize("NFD", c["titre"] or "cours")
    t = re.sub(r"[^a-z0-9]+", "-", "".join(x for x in t if unicodedata.category(x) != "Mn").lower()).strip("-")[:60]
    return f"{c['date'][:10]}-{t or 'cours'}-{c['id'][-6:]}.mp3"


def main():
    attente = [c for c in json.loads(appel("/cours/attente"))["cours"] if c["complet"]]
    if not attente:
        print("Aucun enregistrement à ranger.")
        return
    eps = json.loads(FICHIER.read_text(encoding="utf-8"))
    subprocess.run(["gh", "release", "view", ETIQUETTE], capture_output=True).returncode == 0 or subprocess.run(
        ["gh", "release", "create", ETIQUETTE, "--title", "Cours : audios et PDF", "--notes",
         "Audios enregistrés depuis l'appli, PDF et transcriptions des cours. Ne pas supprimer : l'appli lit les fichiers ici."], check=True)
    ranges, nouveaux = [], []
    for c in attente:
        with tempfile.TemporaryDirectory() as d:
            parties = []
            for n in c["parties"]:
                f = Path(d) / f"p{n:03d}"
                f.write_bytes(appel(f"/cours/partie/{c['id']}/{n}"))
                parties.append(f)
            nom = nom_fichier(c)
            sortie = Path(d) / nom
            entrees = sum((["-i", str(p)] for p in parties), [])
            filtre = "".join(f"[{i}:a]" for i in range(len(parties))) + f"concat=n={len(parties)}:v=0:a=1[a]"
            subprocess.run(["ffmpeg", "-v", "error", "-y", *entrees, "-filter_complex", filtre, "-map", "[a]",
                            "-ac", "1", "-ar", "44100", "-b:a", "48k", str(sortie)], check=True)
            subprocess.run(["gh", "release", "upload", ETIQUETTE, str(sortie), "--clobber"], check=True)
            post = copie_telegram(sortie, c["titre"] or "Cours", duree_s(sortie))
        s = serie_de(c["titre"]) or CF
        num, sous, fin = decouper(c["titre"], s) if s is not CF else (None, c["titre"], False)
        ident = 3_000_000_000 + int(time.time()) - 1_700_000_000 + len(ranges)
        audio = f"{API}/audio/{nom}"
        eps.insert(0, {"id": ident, "serie": s["id"], "num": num, "titre": sous, "fin": fin, "audio": audio,
                       "post": post or audio, "date": c["date"][:10], "source": "appli"})
        ranges.append(c)
        nouveaux.append(ident)
        print(f"Rangé : {c['titre']} → {s['nom']}{f' n° {num}' if num is not None else ''}")
    FICHIER.write_text(json.dumps(eps, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    subprocess.run(["python", str(RACINE / "outils" / "synchro.py"), "--series-seules"], check=False)
    Path(os.environ.get("RANGES", "/tmp/ranges.txt")).write_text("\n".join(c["id"] for c in ranges))
    Path(os.environ.get("NOUVEAUX", "/tmp/nouveaux.txt")).write_text(" ".join(str(i) for i in nouveaux))


if __name__ == "__main__":
    main()
