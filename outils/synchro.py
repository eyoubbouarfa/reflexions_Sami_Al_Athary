"""Synchronisation automatique avec le canal Telegram et le compte SoundCloud.

Lancé chaque jour par GitHub (voir .github/workflows/synchro.yml), ou à la main :
    python outils/synchro.py            # récupère les nouveaux posts
    python outils/synchro.py --tout     # relit tout le canal (dates, titres, cours manquants)

- Telegram : lit la version web publique du canal, avec la vraie date de chaque post.
- SoundCloud : liste les pistes du compte et ajoute les épisodes numérotés absents de Telegram.
- Ne supprime jamais rien. Ne se base sur aucune cadence : chaque cours est classé par son titre.
"""
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from import_telegram import decouper, serie_de, sans_accents, LIEN_AUDIO  # noqa: E402
from series import SERIES, THEMES  # noqa: E402

CANAL = "Sami_Athary"
SOUNDCLOUD = "https://soundcloud.com/cours-religieux/tracks"
RACINE = Path(__file__).resolve().parent.parent
FICHIER = RACINE / "data" / "episodes.json"
CF = next(s for s in SERIES if s["code"] == "CF")


class Page(HTMLParser):
    """Extrait les posts de https://t.me/s/<canal> : id, date, texte, liens, type de média."""

    def __init__(self):
        super().__init__()
        self.posts, self.cur, self.pile, self.dans_texte = [], None, [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "")
        if tag == "div" and "tgme_widget_message " in cls + " " and a.get("data-post", "").startswith(CANAL + "/"):
            self.cur = {"id": int(a["data-post"].split("/")[1]), "texte": "", "liens": [], "media": None, "date": ""}
            self.posts.append(self.cur)
        if not self.cur:
            return
        if tag == "div" and "tgme_widget_message_text" in cls:
            self.dans_texte = 1
        elif self.dans_texte and tag == "div":
            self.dans_texte += 1
        if self.dans_texte and tag == "br":
            self.cur["texte"] += "\n"
        if tag == "a" and a.get("href"):
            self.cur["liens"].append(a["href"])
        if tag == "time" and a.get("datetime") and not self.cur["date"]:
            self.cur["date"] = a["datetime"]
        if "tgme_widget_message_voice" in cls or "tgme_widget_message_document" in cls or "audio" in cls:
            self.cur["media"] = self.cur["media"] or "audio"
        if "tgme_widget_message_video" in cls or "roundvideo" in cls:
            self.cur["media"] = "video"
        if "tgme_widget_message_document_title" in cls:
            self.cur["doc_titre"] = True

    def handle_endtag(self, tag):
        if self.dans_texte and tag == "div":
            self.dans_texte -= 1

    def handle_data(self, data):
        if self.cur and self.dans_texte:
            self.cur["texte"] += data


def lire(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (synchro des cours)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def posts_telegram(depuis_id, tout):
    vus, avant = {}, None
    for _ in range(200):
        url = f"https://t.me/s/{CANAL}" + (f"?before={avant}" if avant else "")
        p = Page()
        p.feed(lire(url))
        if not p.posts:
            break
        for x in p.posts:
            vus[x["id"]] = x
        plus_petit = min(x["id"] for x in p.posts)
        if (not tout and plus_petit <= depuis_id) or plus_petit <= 1 or plus_petit == avant:
            break
        avant = plus_petit
        time.sleep(1.5)
    return sorted(vus.values(), key=lambda x: x["id"])


def episode_depuis_post(x):
    texte = html.unescape(x["texte"]).strip()
    url = next((l for l in x["liens"] if LIEN_AUDIO.match(l)), None)
    if not url and x["media"] == "audio":
        url = f"https://t.me/{CANAL}/{x['id']}"
    if not url or not texte:
        return None
    texte = re.sub(r"\s*par Cours religieux( sur #?SoundCloud)?", "", texte, flags=re.I)
    texte = re.sub(r"^\s*(Écoutez|Ecoutez)\s+", "", texte)
    lignes = [re.sub(r"^[\s🎧🔊🎙️▶️•\-–]*(écouter|ecouter)\s*:?\s*", "", LIEN_AUDIO.sub("", l), flags=re.I).strip(" :-–")
              for l in texte.splitlines()]
    lignes = [l for l in lignes if l]
    numerotees = [l for l in lignes if re.match(r"^\d{1,4}\b", l)]
    titre = (numerotees or lignes or [""])[0]
    if not titre or re.match(r"^(Vidéo|Video|Document|Photo|Audio) de ", titre) or re.match(r"^[#\W]", titre[0]) \
            or titre.lower().startswith("retrouvez sur cette playlist"):
        return None  # annonces, rappels écrits, médias sans titre : pas des cours
    s = serie_de(titre) or CF
    num, sous, fin = decouper(titre, s) if s is not CF else (None, titre, False)
    if "goo.gl" in url:
        url = f"https://t.me/{CANAL}/{x['id']}"
    return {"id": x["id"], "serie": s["id"], "num": num, "titre": sous, "fin": fin,
            "audio": url.split("?")[0], "post": f"https://t.me/{CANAL}/{x['id']}", "date": x["date"][:10],
            "_reconnu": s is not CF, "_titre": titre}


def maj_series(liste):
    """Recalcule data/series.json (nombre de cours par série) d'après la liste des cours."""
    fs = RACINE / "data" / "series.json"
    anciennes = {s["id"]: s for s in json.loads(fs.read_text(encoding="utf-8"))["series"]}
    pub = []
    for s in SERIES:
        nb = sum(1 for e in liste if e["serie"] == s["id"])
        if nb:
            d = {k: v for k, v in s.items() if k not in ("motifs", "code")} | {"nb": nb}
            if anciennes.get(s["id"], {}).get("support"):
                d["support"] = anciennes[s["id"]]["support"]
            pub.append(d)
    fs.write_text(json.dumps({"themes": THEMES, "series": pub}, ensure_ascii=False, indent=1), encoding="utf-8")


def pistes_soundcloud():
    try:
        r = subprocess.run(["yt-dlp", "--flat-playlist", "-J", SOUNDCLOUD], capture_output=True, text=True, timeout=900)
        return json.loads(r.stdout).get("entries", []) if r.returncode == 0 else []
    except Exception as e:  # SoundCloud indisponible : on continue avec Telegram seul
        print("SoundCloud non lu :", e)
        return []


def main():
    tout = "--tout" in sys.argv
    if "--series-seules" in sys.argv:
        maj_series(json.loads(FICHIER.read_text(encoding="utf-8")))
        return
    eps = {e["id"]: e for e in json.loads(FICHIER.read_text(encoding="utf-8"))}
    dernier = max((i for i in eps if i < 1_000_000), default=0)

    ajouts, maj, inconnus = 0, 0, []
    nouveaux = []
    posts_appli = {e["post"] for e in eps.values() if e.get("source") == "appli"}
    appli = {(e["serie"], e["num"]): e for e in eps.values() if e.get("source") == "appli" and e["num"] is not None}
    for x in posts_telegram(dernier, tout):
        e = episode_depuis_post(x)
        if not e:
            continue
        reconnu, titre = e.pop("_reconnu"), e.pop("_titre")
        ancien = eps.get(e["id"])
        if ancien:
            if e["date"] and ancien.get("date") != e["date"]:
                ancien["date"] = e["date"]; maj += 1
            continue
        if e["post"] in posts_appli:  # post fait par le robot à partir d'un enregistrement de l'appli
            continue
        double = appli.get((e["serie"], e["num"])) if e["num"] is not None else None
        if double:  # déjà enregistré depuis l'appli : on garde l'audio de l'appli, on note juste le lien Telegram
            double["post"] = e["post"]
            continue
        if not reconnu:
            inconnus.append((e["id"], titre))
        eps[e["id"]] = e
        ajouts += 1
        nouveaux.append(e["id"])

    # SoundCloud : épisodes numérotés jamais postés sur Telegram
    connus = {(e["serie"], e["num"]) for e in eps.values() if e["num"] is not None}
    for p in pistes_soundcloud():
        titre, url = (p.get("title") or "").strip(), (p.get("url") or "").split("?")[0]
        titre = re.sub(r"\s*par Cours religieux.*$", "", titre, flags=re.I)
        if not titre or not url:
            continue
        s = serie_de(titre)
        if not s:
            continue
        num, sous, fin = decouper(titre, s)
        if num is None or (s["id"], num) in connus:
            continue
        ident = int(p["id"]) if str(p.get("id", "")).isdigit() else abs(hash(url)) % 10**9 + 10**9
        date = datetime.utcfromtimestamp(p["timestamp"]).strftime("%Y-%m-%d") if p.get("timestamp") else ""
        eps[ident] = {"id": ident, "serie": s["id"], "num": num, "titre": sous, "fin": fin,
                      "audio": url, "post": url, "date": date, "source": "soundcloud"}
        connus.add((s["id"], num))
        ajouts += 1
        nouveaux.append(ident)

    liste = sorted(eps.values(), key=lambda e: (e.get("date") or "0000", e["id"] if e["id"] < 1_000_000 else 0), reverse=True)
    FICHIER.write_text(json.dumps(liste, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    maj_series(liste)

    # Liste des nouveaux cours : leur PDF est fabriqué ensuite automatiquement
    Path(os.environ.get("NOUVEAUX", "/tmp/nouveaux.txt")).write_text(" ".join(str(i) for i in nouveaux))
    print(f"{ajouts} cours ajoutés, {maj} dates complétées, {len(liste)} au total.")
    for i, t in inconnus:
        print(f"  non classé (Conférences) : {i} {t}")


if __name__ == "__main__":
    main()
