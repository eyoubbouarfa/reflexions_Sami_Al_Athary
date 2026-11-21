"""Publie dans l'appli les notes de cours VALIDÉES par l'enseignant.

Chaque cours a un fichier notes/<id>.md, par exemple notes/1814.md :

    ---
    valide: oui
    ---
    ## Le pèlerinage d'adieu
    Texte du cours, paragraphe par paragraphe.

    > ar: إِنَّ دِمَاءَكُمْ وَأَمْوَالَكُمْ حَرَامٌ عَلَيْكُمْ

    ![Schéma du trajet du pèlerinage](illustrations/1814-trajet.svg)

- "## " : intertitre. "> ar: " : passage en arabe (verset, hadith). "![légende](image)" : illustration.
- Tant que "valide: oui" n'est pas présent, la note reste hors de l'appli.

Usage :
    python outils/publier_notes.py
Résultat : data/textes.json, lu par l'appli (affichage, PDF et recherche dans le contenu).
"""
import html
import json
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


def en_html(md):
    blocs, texte = [], []
    for para in re.split(r"\n\s*\n", md.strip()):
        para = para.strip()
        if para.startswith("## "):
            t = para[3:].strip()
            blocs.append(f"<h4>{html.escape(t)}</h4>"); texte.append(t)
        elif para.startswith("> ar:"):
            t = para[5:].strip()
            blocs.append(f'<p class="ar">{html.escape(t)}</p>'); texte.append(t)
        elif m := re.match(r"!\[(.*?)\]\((.*?)\)", para):
            blocs.append(f'<figure><img src="{html.escape(m.group(2))}" alt="{html.escape(m.group(1))}" loading="lazy">'
                         f'<figcaption class="muted small">{html.escape(m.group(1))}</figcaption></figure>')
        else:
            t = " ".join(l.strip() for l in para.splitlines())
            h = html.escape(t)
            h = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", h)
            blocs.append(f"<p>{h}</p>"); texte.append(t.replace("**", ""))
    return "\n".join(blocs), "\n".join(texte)


def main():
    dossier = RACINE / "notes"
    textes, attente = {}, []
    for f in sorted(dossier.glob("*.md")) if dossier.exists() else []:
        brut = f.read_text(encoding="utf-8")
        entete = re.match(r"^---\n(.*?)\n---\n", brut, re.S)
        if not entete or not re.search(r"^valide:\s*oui\s*$", entete.group(1), re.M | re.I):
            attente.append(f.stem); continue
        h, t = en_html(brut[entete.end():])
        textes[f.stem] = {"html": h, "texte": t}
    (RACINE / "data" / "textes.json").write_text(json.dumps(textes, ensure_ascii=False), encoding="utf-8")
    print(f"{len(textes)} notes publiées." + (f" En attente de relecture : {', '.join(attente)}" if attente else ""))


if __name__ == "__main__":
    main()
