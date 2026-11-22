"""Synthèse d'un cours à partir de sa transcription, avec un modèle d'IA (GitHub Models, gratuit et limité).

Usage : python outils/enrichir.py 1823 ...   (dans GitHub Actions, permission « models: read »)
Lit    : data/transcriptions/<id>.json
Écrit  : data/ia/<id>.json  {plan, points, references, resume, modele}

Règle absolue : l'IA ne fait que structurer ce que l'enseignant a dit. Elle n'ajoute aucun verset, hadith,
savant ou avis qui ne soit pas dans la transcription, et ne juge pas l'authenticité des hadiths.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
TR = RACINE / "data" / "transcriptions"
SORTIE = RACINE / "data" / "ia"
URL = "https://models.github.ai/inference/chat/completions"
MODELES = ["openai/gpt-4.1-mini", "openai/gpt-4o-mini"]
TAILLE_MORCEAU = 11000  # caractères, pour rester sous la limite de l'offre gratuite

CONSIGNES = """Tu aides à mettre en forme la transcription d'un cours de sciences islamiques donné en français par Sami al Athary.
Règles absolues :
1. Tu n'utilises QUE ce qui est dit dans la transcription. Tu n'ajoutes aucun verset, hadith, savant, avis, date ou explication qui n'y figure pas, même si tu le connais.
2. Tu ne juges pas l'authenticité d'un hadith et tu n'en donnes pas le degré, sauf si l'enseignant le dit lui-même : tu rapportes alors ses mots.
3. Tu ne donnes aucun avis, aucune fatwa, aucune conclusion personnelle. Tu restes neutre et fidèle.
4. Les passages en arabe ne sont pas transcrits ([arabe]) : tu ne devines jamais leur contenu.
5. La transcription automatique contient des erreurs : si un passage est incompréhensible, tu l'ignores au lieu de l'interpréter.
6. Tu écris en français simple, sans formule de politesse, en restant au plus près des mots de l'enseignant."""


def appel(messages):
    jeton = os.environ["GITHUB_TOKEN"]
    derniere = None
    for modele in MODELES:
        for essai in range(4):
            corps = json.dumps({"model": modele, "messages": messages, "temperature": 0.1,
                                "response_format": {"type": "json_object"}}).encode()
            req = urllib.request.Request(URL, data=corps, headers={"Authorization": f"Bearer {jeton}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    rep = json.loads(r.read())
                return json.loads(rep["choices"][0]["message"]["content"]), modele
            except urllib.error.HTTPError as e:
                derniere = f"{e.code} {e.read()[:300]!r}"
                if e.code == 429:
                    time.sleep(min(60 * (essai + 1), 240)); continue
                break
            except Exception as e:  # noqa: BLE001
                derniere = str(e); time.sleep(10)
    raise RuntimeError(f"Modèle injoignable : {derniere}")


def mm_ss(s):
    s = int(s); return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def morceaux(segments):
    courant, debut, out = [], None, []
    for s in segments:
        ligne = f"[{mm_ss(s['debut'])}] " + ("[arabe]" if s["arabe"] else s["texte"])
        if debut is None:
            debut = s["debut"]
        courant.append(ligne)
        if sum(len(x) for x in courant) > TAILLE_MORCEAU:
            out.append("\n".join(courant)); courant, debut = [], None
    if courant:
        out.append("\n".join(courant))
    return out


def enrichir(ident):
    tr = json.loads((TR / f"{ident}.json").read_text(encoding="utf-8"))
    parts, modele = [], None
    for i, m in enumerate(morceaux(tr["segments"]), 1):
        r, modele = appel([{"role": "system", "content": CONSIGNES},
                           {"role": "user", "content": "Voici une partie de la transcription (avec les minutages).\n"
                            "Réponds en JSON : {\"points\": [idées principales dites par l'enseignant, 1 phrase chacune, max 6], "
                            "\"references\": [{\"type\": \"coran\"|\"hadith\"|\"savant\"|\"livre\", \"cite\": ce que l'enseignant cite, tel qu'il le dit, "
                            "\"moment\": minutage}], \"titre_partie\": titre court de cette partie}.\n"
                            "Une référence n'est listée que si l'enseignant la mentionne explicitement.\n\n" + m}])
        parts.append(r)
        print(f"{ident} : partie {i} faite")
    final, modele = appel([{"role": "system", "content": CONSIGNES},
                           {"role": "user", "content": "Voici les notes des parties successives d'un même cours. "
                            "Réponds en JSON : {\"resume\": résumé fidèle du cours en 4 à 6 phrases, "
                            "\"plan\": [titres des grandes parties, dans l'ordre], \"points\": [les 5 à 8 enseignements principaux]}. "
                            "N'ajoute rien qui ne soit pas dans les notes.\n\n" + json.dumps(parts, ensure_ascii=False)}])
    refs, vus = [], set()
    for p in parts:
        for r in p.get("references", []) or []:
            cle = (r.get("type"), (r.get("cite") or "").strip().lower())
            if cle[1] and cle not in vus:
                vus.add(cle); refs.append(r)
    out = {"id": ident, "modele": modele, "resume": final.get("resume", ""), "plan": final.get("plan", []),
           "points": final.get("points", []), "references": refs}
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / f"{ident}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{ident} : synthèse écrite ({modele}, {len(refs)} références)")


if __name__ == "__main__":
    for i in sys.argv[1:]:
        enrichir(int(i))
