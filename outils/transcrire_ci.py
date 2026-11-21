"""Transcrit des cours sur les serveurs gratuits de GitHub (voir .github/workflows/cours-pdf.yml).

Usage : python outils/transcrire_ci.py 1823 1814 ...
Résultat : data/transcriptions/<id>.json (segments horodatés, en français uniquement).

Les passages en arabe ne sont PAS retranscrits : ils sont repérés (détection de langue par
fenêtres de 30 s, écriture arabe, faible confiance) et remplacés par un repère « passage en arabe ».
"""
import json
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
AUDIO = RACINE / "audios"
SORTIE = RACINE / "data" / "transcriptions"
ARABE = re.compile(r"[؀-ۿ]")
AMORCE = ("Cours de sciences islamiques en français. Allah, le Prophète, hadith, sourate, verset, "
          "tawhid, Sunna, imam Malik, al Boukhary, Muslim, al Albâny, Compagnons, qu'Allah l'agrée.")


def telecharger(ep):
    AUDIO.mkdir(exist_ok=True)
    cible = AUDIO / f"{ep['id']}.mp3"
    if not cible.exists():
        subprocess.run(["yt-dlp", "-q", "-x", "--audio-format", "mp3", "-o", str(AUDIO / f"{ep['id']}.%(ext)s"), ep["audio"]], check=True)
    return cible


def fenetres_arabes(modele, audio, pas=30):
    """Renvoie les intervalles (début, fin) en secondes où l'arabe domine."""
    from faster_whisper.audio import decode_audio  # noqa
    sr = 16000
    zones = []
    for debut in range(0, int(len(audio) / sr), pas):
        bout = audio[debut * sr:(debut + pas) * sr]
        if len(bout) < sr * 3:
            continue
        try:
            langue, proba, toutes = modele.detect_language(bout)
            p_ar = dict(toutes).get("ar", 0.0) if toutes else (proba if langue == "ar" else 0.0)
        except Exception:
            return []  # détection indisponible : on se rabat sur les autres indices
        if p_ar > 0.5:
            zones.append((debut, debut + pas))
    return zones


def main(ids):
    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio
    eps = {e["id"]: e for e in json.loads((RACINE / "data" / "episodes.json").read_text(encoding="utf-8"))}
    modele = WhisperModel("medium", device="cpu", compute_type="int8")
    SORTIE.mkdir(parents=True, exist_ok=True)
    for i in ids:
        ep = eps[int(i)]
        fichier = telecharger(ep)
        audio = decode_audio(str(fichier))
        zones = fenetres_arabes(modele, audio)
        segs, _info = modele.transcribe(audio, language="fr", initial_prompt=AMORCE, vad_filter=True, beam_size=1)
        sortie = []
        for s in segs:
            milieu = (s.start + s.end) / 2
            en_arabe = any(a <= milieu < b for a, b in zones) or ARABE.search(s.text) or s.avg_logprob < -1.2
            if en_arabe:
                if sortie and sortie[-1]["arabe"]:
                    sortie[-1]["fin"] = round(s.end, 1)
                else:
                    sortie.append({"debut": round(s.start, 1), "fin": round(s.end, 1), "texte": "", "arabe": True})
            else:
                sortie.append({"debut": round(s.start, 1), "fin": round(s.end, 1), "texte": s.text.strip(), "arabe": False})
        duree = round(len(audio) / 16000)
        (SORTIE / f"{ep['id']}.json").write_text(json.dumps({"id": ep["id"], "duree": duree, "segments": sortie},
                                                            ensure_ascii=False, indent=0), encoding="utf-8")
        print(f"{ep['id']} : {len(sortie)} segments, {sum(1 for x in sortie if x['arabe'])} passages en arabe écartés")


if __name__ == "__main__":
    main(sys.argv[1:])
