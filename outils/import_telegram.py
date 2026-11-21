"""Met à jour data/episodes.json à partir de l'export Telegram du canal.

Telegram Desktop > canal > ⋮ > Exporter l'historique > aucun média, format JSON > result.json
Usage :
    python outils/import_telegram.py chemin/vers/result.json

- Ajoute les nouveaux cours, corrige les titres des anciens, ne supprime rien.
- Les cours qu'aucune série ne reconnaît sont listés : ajoute leurs motifs dans outils/series.py puis relance.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from series import SERIES, THEMES  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
LIEN_AUDIO = re.compile(r"https?://(?:on\.|m\.|www\.)?soundcloud\.com/[^\s)]+|https?://soundcloud\.app\.goo\.gl/\S+", re.I)
ARABE = re.compile(r"^[؀-ۿ\sً-ٰٟ]+$")


def sans_accents(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().replace("’", "'")


def texte_brut(msg):
    t = msg.get("text", "")
    return "".join(p if isinstance(p, str) else p.get("text", "") for p in t) if isinstance(t, list) else t


def lien(msg):
    for ent in msg.get("text_entities", []) or []:
        href = ent.get("href") or (ent.get("text") if ent.get("type") == "link" else "")
        if href and LIEN_AUDIO.match(href):
            return href.split("?")[0]
    m = LIEN_AUDIO.search(texte_brut(msg))
    if m:
        return m.group(0).split("?")[0]
    if msg.get("media_type") in ("audio_file", "voice_message"):
        return f"https://t.me/Sami_Athary/{msg['id']}"
    return None


def titre(msg):
    lignes = []
    for l in texte_brut(msg).splitlines():
        l = LIEN_AUDIO.sub("", l)
        l = re.sub(r"^[\s🎧🔊🎙️▶️•\-–]*(écouter|ecouter)\s*:?\s*", "", l, flags=re.I).strip(" :-–")
        if l:
            lignes.append(l)
    num = [l for l in lignes if re.match(r"^\d{1,4}\b", l)]
    return (num or lignes or [msg.get("title") or ""])[0]


def serie_de(t):
    n = sans_accents(t)
    for s in SERIES:  # l'ordre du fichier series.py compte : les séries précises avant les génériques
        if any(m in n for m in s["motifs"]):
            return s
    return None


def decouper(t, s):
    m = re.match(r"^(\d{1,4})\s*(?:/\d+)?\s*((?:et\s+)?fin)?\s*-?\s*(.*)$", t, flags=re.I)
    num = int(m.group(1)) if m else None
    fin = bool(m and m.group(2)) or bool(re.search(r"\bet fin\b", t, re.I))
    reste = m.group(3) if m else t
    morceaux = [p.strip() for p in re.split(r"\s+-\s+|\s*-\s+|\s+-\s*", reste) if p.strip()]
    utiles = [p for p in morceaux
              if (s["type"] == "preche" or not any(mo in sans_accents(p) for mo in s["motifs"]))
              and not ARABE.match(p)
              and not re.match(r"^(sheykh|sheyh|cheikh|l'imam|al hafidh|sermon)", sans_accents(p))
              and "(ar/fr)" not in p.lower()]
    sous = " - ".join(utiles)
    if sans_accents(sous) == sans_accents(s["nom"]):
        sous = ""
    return num, sous, fin


def main(chemin):
    export = json.loads(Path(chemin).read_text(encoding="utf-8"))
    fichier = RACINE / "data" / "episodes.json"
    eps = {e["id"]: e for e in json.loads(fichier.read_text(encoding="utf-8"))} if fichier.exists() else {}
    nouveaux, inconnus = 0, []
    for msg in export.get("messages", []):
        if msg.get("type") != "message":
            continue
        url = lien(msg)
        if not url:
            continue
        t = titre(msg)
        s = serie_de(t)
        if not s:
            inconnus.append((msg["id"], t))
            s = next(x for x in SERIES if x["code"] == "CF")
        num, sous, fin = decouper(t, s) if s["code"] != "CF" else (None, t, False)
        ancien = eps.get(msg["id"], {})
        e = {"id": msg["id"], "serie": s["id"], "num": num, "titre": sous, "fin": fin,
             "audio": url if "goo.gl" not in url else f"https://t.me/Sami_Athary/{msg['id']}",
             "post": f"https://t.me/Sami_Athary/{msg['id']}", "date": (msg.get("date") or "")[:10]}
        if ancien.get("audio", "").startswith("https://soundcloud.com/"):
            e["audio"] = ancien["audio"]  # garde le lien complet déjà résolu
        nouveaux += msg["id"] not in eps
        eps[msg["id"]] = e

    liste = sorted(eps.values(), key=lambda e: e["id"], reverse=True)
    fichier.write_text(json.dumps(liste, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    series_pub = []
    for s in SERIES:
        nb = sum(1 for e in liste if e["serie"] == s["id"])
        if nb:
            series_pub.append({k: v for k, v in s.items() if k not in ("motifs", "code")} | {"nb": nb})
    ancien_series = RACINE / "data" / "series.json"
    if ancien_series.exists():  # conserve les liens de support déjà renseignés
        supports = {s["id"]: s.get("support") for s in json.loads(ancien_series.read_text(encoding="utf-8"))["series"]}
        for s in series_pub:
            if supports.get(s["id"]):
                s["support"] = supports[s["id"]]
    ancien_series.write_text(json.dumps({"themes": THEMES, "series": series_pub}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(liste)} cours au total, dont {nouveaux} nouveaux.")
    if inconnus:
        print(f"\n{len(inconnus)} cours rangés dans « Conférences » faute de série reconnue :")
        for i, t in inconnus[:50]:
            print(f"  {i}  {t}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
