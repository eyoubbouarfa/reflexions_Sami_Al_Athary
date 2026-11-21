"""Télécharge les audios d'une série et les transcrit en texte, hors ligne, sur ton PC.

Installation (une seule fois) :
    pip install yt-dlp faster-whisper
    + ffmpeg installé (https://ffmpeg.org)

Usage :
    python outils/transcrire.py sira-qr            # toute la série
    python outils/transcrire.py muwatta --max 5     # les 5 premiers épisodes pas encore transcrits
    python outils/transcrire.py --id 1814 1807      # des cours précis

Résultat : transcriptions/<id>.txt (texte brut, NON publié dans l'appli).
Les notes publiées passent par notes/<id>.md puis outils/publier_notes.py, après relecture.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
AUDIO = RACINE / "audios"
SORTIE = RACINE / "transcriptions"

# Vocabulaire fréquent dans les cours : aide la reconnaissance des termes arabes
AMORCE = ("Cours de sciences islamiques en français avec des citations en arabe. "
          "Allah, le Prophète ﷺ, hadith, sourate, verset, tawhid, Sunna, salaf, imam Malik, "
          "al Boukhary, Muslim, al Albâny, Muwatta, fiqh, ablutions, prière, Compagnons, qu'Allah l'agrée.")


def episodes(args):
    eps = json.loads((RACINE / "data" / "episodes.json").read_text(encoding="utf-8"))
    if args.id:
        choix = [e for e in eps if e["id"] in args.id]
    else:
        choix = sorted([e for e in eps if e["serie"] == args.serie], key=lambda e: (e["num"] or 0, e["id"]))
    choix = [e for e in choix if not (SORTIE / f"{e['id']}.txt").exists()]
    return choix[: args.max] if args.max else choix


def telecharger(e):
    AUDIO.mkdir(exist_ok=True)
    cible = AUDIO / f"{e['id']}.mp3"
    if cible.exists():
        return cible
    if "t.me/" in e["audio"]:
        print(f"  {e['id']} : audio hébergé sur Telegram, télécharge-le à la main dans audios/{e['id']}.mp3")
        return None
    r = subprocess.run(["yt-dlp", "-x", "--audio-format", "mp3", "-o", str(AUDIO / f"{e['id']}.%(ext)s"), e["audio"]])
    return cible if r.returncode == 0 and cible.exists() else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("serie", nargs="?")
    p.add_argument("--id", type=int, nargs="*")
    p.add_argument("--max", type=int)
    p.add_argument("--modele", default="large-v3", help="large-v3 (précis, lent) ou medium (plus rapide)")
    args = p.parse_args()
    if not args.serie and not args.id:
        sys.exit(__doc__)

    from faster_whisper import WhisperModel
    modele = WhisperModel(args.modele, device="auto", compute_type="auto")
    SORTIE.mkdir(exist_ok=True)
    liste = episodes(args)
    print(f"{len(liste)} cours à transcrire")
    for e in liste:
        fichier = telecharger(e)
        if not fichier:
            continue
        print(f"  {e['id']} n°{e['num']} : transcription…")
        segments, _ = modele.transcribe(str(fichier), language="fr", initial_prompt=AMORCE, vad_filter=True)
        lignes = []
        for s in segments:
            m, sec = divmod(int(s.start), 60)
            lignes.append(f"[{m:02d}:{sec:02d}] {s.text.strip()}")
        (SORTIE / f"{e['id']}.txt").write_text("\n".join(lignes), encoding="utf-8")
        print(f"  {e['id']} : ok ({len(lignes)} segments)")


if __name__ == "__main__":
    main()
