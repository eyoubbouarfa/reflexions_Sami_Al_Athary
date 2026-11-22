"""Remplace, pour le lecteur intégré, les liens courts SoundCloud (on.soundcloud.com/…) par l'adresse complète.

Le lecteur SoundCloud de l'appli (et le saut au bon moment depuis le texte) a besoin de l'adresse complète.
Écrit le champ « sc » des cours concernés dans data/episodes.json ; le champ « audio » n'est pas touché.
"""
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

FICHIER = Path(__file__).resolve().parent.parent / "data" / "episodes.json"


class SansSuivre(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


ouvreur = urllib.request.build_opener(SansSuivre)


def resoudre(url):
    try:
        ouvreur.open(urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"}), timeout=20)
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location", "")
        if loc.startswith("https://soundcloud.com/"):
            return loc.split("?")[0]
    except Exception:  # noqa: BLE001
        pass
    return None


eps = json.loads(FICHIER.read_text(encoding="utf-8"))
a_faire = [e for e in eps if e["audio"].startswith("https://on.soundcloud.com/") and not e.get("sc")]
with ThreadPoolExecutor(8) as ex:
    for e, url in zip(a_faire, ex.map(resoudre, [e["audio"] for e in a_faire])):
        if url:
            e["sc"] = url
FICHIER.write_text(json.dumps(eps, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"{sum(1 for e in a_faire if e.get('sc'))}/{len(a_faire)} liens courts SoundCloud résolus")
