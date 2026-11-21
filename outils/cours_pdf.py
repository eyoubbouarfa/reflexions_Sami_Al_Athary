"""Construit le PDF d'un cours à partir de sa transcription, sans rédaction par IA.

Usage : python outils/cours_pdf.py 1823 [1814 ...]
Lit   : data/transcriptions/<id>.json, data/episodes.json, data/series.json, data/validations.json
Écrit : data/pdf/<id>.pdf

Contenu : fiche du cours, mention de validation (tampon de Sami s'il a validé, sinon mention
« non relu »), trois illustrations calculées automatiquement (place dans la série, déroulé du
cours, mots-clés), puis le texte découpé en parties horodatées. L'arabe n'est jamais retranscrit.
"""
import collections
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,  # noqa: E402
                                Spacer, Table, TableStyle)

RACINE = Path(__file__).resolve().parent.parent
DATA = RACINE / "data"
VERT, VERT2, OR, OR_CLAIR, ENCRE, GRIS = "#0E3B2C", "#14523D", "#A8833F", "#F5EDDB", "#11261D", "#5D6F66"

POLICES = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
for nom, f in [("Sans", "DejaVuSans.ttf"), ("Sans-B", "DejaVuSans-Bold.ttf"), ("Sans-I", "DejaVuSans-Oblique.ttf"),
               ("Serif", "DejaVuSerif.ttf"), ("Serif-B", "DejaVuSerif-Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(nom, os.path.join(POLICES, f)))
plt.rcParams["font.family"] = "DejaVu Sans"

MOTS_VIDES = set("""alors aussi autre autres avant avec avoir bien cela celle celles celui cette ceux chez comme comment dans
depuis donc elle elles encore entre était étaient être fait faire faut leur leurs lorsque mais même mêmes nous parce
pendant peut peuvent plus pour pourquoi quand quelle quelles quelque quels quoi sans selon sera seront sont sous surtout
tous tout toute toutes très vers voilà vous également ainsi après celui-ci c'est qu'il qu'ils qu'elle n'est d'un d'une
c'était cela s'il jusqu'à parmi chose choses dire dit disait veut veux voir vient venu gens fois rien beaucoup
justement exemple vraiment effectivement maintenant ensuite certes notamment simplement toujours jamais donc
celui-là celle-ci ceci comme lorsqu'il puisque quelqu'un d'autres l'on avez avons allez allons aller""".split())

ESSENTIEL = lambda t: (t or "").replace("ﷺ", "(paix et salut sur lui)")


def hms(s):
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"


def norm(m):
    return "".join(c for c in unicodedata.normalize("NFD", m.lower()) if unicodedata.category(c) != "Mn")


def mots_cles(texte, n=12):
    mots = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]{5,}", texte)
    compte = collections.Counter()
    forme = {}
    for m in mots:
        m = m.strip("'’-")
        if "'" in m or "’" in m:
            m = re.split(r"['’]", m)[-1]
        if len(m) < 5 or norm(m) in {norm(x) for x in MOTS_VIDES}:
            continue
        k = norm(m)
        compte[k] += 1
        forme.setdefault(k, m.lower())
    return [(forme[k], c) for k, c in compte.most_common(n)]


def parties(segments, duree_cible=360):
    """Découpe le cours en parties d'environ 6 min, en coupant sur une pause ou un passage en arabe."""
    blocs, cour = [], []
    debut = 0
    for s in segments:
        if cour and s["debut"] - debut >= duree_cible and (s["arabe"] or not cour[-1]["arabe"]):
            blocs.append(cour)
            cour, debut = [], s["debut"]
        if not cour:
            debut = s["debut"]
        cour.append(s)
    if cour:
        blocs.append(cour)
    return blocs


# ---------- illustrations ----------
def fig_serie(ep, freres, chemin):
    nums = sorted(e["num"] for e in freres if e["num"] is not None)
    fig, ax = plt.subplots(figsize=(7.2, 1.25), dpi=200)
    ax.axhline(0, color=VERT, lw=2, zorder=1)
    if nums:
        lo, hi = nums[0], nums[-1]
        ax.scatter(nums, [0] * len(nums), s=8, color=VERT2, zorder=2)
        if ep["num"] is not None:
            ax.scatter([ep["num"]], [0], s=180, color=OR, zorder=3, edgecolor="white", lw=1.5)
            ax.annotate(f"Ce cours : n° {ep['num']}", (ep["num"], 0), xytext=(0, 14), textcoords="offset points",
                        ha="center", fontsize=9, color=ENCRE, weight="bold")
        ax.annotate(f"n° {lo}", (lo, 0), xytext=(0, -16), textcoords="offset points", ha="center", fontsize=8, color=GRIS)
        ax.annotate(f"n° {hi}", (hi, 0), xytext=(0, -16), textcoords="offset points", ha="center", fontsize=8, color=GRIS)
        ax.set_xlim(lo - (hi - lo) * .04 - 1, hi + (hi - lo) * .04 + 1)
    ax.set_ylim(-1, 1)
    ax.axis("off")
    fig.savefig(chemin, bbox_inches="tight", transparent=True)
    plt.close(fig)


def fig_deroule(segments, blocs, duree, chemin):
    fig, ax = plt.subplots(figsize=(7.2, 1.5), dpi=200)
    for s in segments:
        ax.barh(0, max(s["fin"] - s["debut"], 1), left=s["debut"], height=.6,
                color=OR if s["arabe"] else VERT2, lw=0)
    for i, b in enumerate(blocs, 1):
        x = b[0]["debut"]
        ax.axvline(x, color="white", lw=1.2)
        ax.text(x + duree * .005, .52, f"{i}", fontsize=8, color=ENCRE, weight="bold", va="bottom")
    ax.set_xlim(0, duree)
    ax.set_ylim(-.5, 1)
    ax.set_yticks([])
    ticks = list(range(0, int(duree) + 1, 600 if duree > 2400 else 300))
    ax.set_xticks(ticks, [hms(t) for t in ticks], fontsize=7, color=GRIS)
    for c in ("top", "right", "left"):
        ax.spines[c].set_visible(False)
    ax.spines["bottom"].set_color("#cccccc")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=VERT2, label="Explication en français"), Patch(color=OR, label="Passages en arabe (non retranscrits)")],
              loc="upper center", bbox_to_anchor=(.5, -.42), ncol=2, frameon=False, fontsize=7.5)
    fig.savefig(chemin, bbox_inches="tight", transparent=True)
    plt.close(fig)


def fig_mots(mc, chemin):
    mc = mc[:10][::-1]
    fig, ax = plt.subplots(figsize=(7.2, 2.9), dpi=200)
    ax.barh([m for m, _ in mc], [c for _, c in mc], color=VERT2, height=.62)
    for i, (_, c) in enumerate(mc):
        ax.text(c, i, f"  {c}", va="center", fontsize=8, color=GRIS)
    ax.tick_params(axis="y", labelsize=9, colors=ENCRE, length=0)
    ax.set_xticks([])
    for c in ("top", "right", "bottom"):
        ax.spines[c].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    fig.savefig(chemin, bbox_inches="tight", transparent=True)
    plt.close(fig)


# ---------- PDF ----------
S = {
    "titre": ParagraphStyle("t", fontName="Serif-B", fontSize=21, leading=26, textColor=VERT, alignment=TA_CENTER, spaceAfter=4),
    "sous": ParagraphStyle("s", fontName="Sans", fontSize=10.5, leading=14, textColor=OR, alignment=TA_CENTER, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName="Serif-B", fontSize=14, leading=18, textColor=VERT, spaceBefore=10, spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName="Sans-B", fontSize=10.5, leading=14, textColor=VERT2, spaceBefore=8, spaceAfter=3),
    "corps": ParagraphStyle("c", fontName="Serif", fontSize=10.5, leading=15.5, textColor=ENCRE, alignment=TA_JUSTIFY, spaceAfter=6),
    "petit": ParagraphStyle("p", fontName="Sans", fontSize=8.5, leading=11.5, textColor=GRIS),
    "ar": ParagraphStyle("ar", fontName="Sans-I", fontSize=9, leading=12, textColor=OR, spaceAfter=6, leftIndent=8),
    "mention": ParagraphStyle("m", fontName="Sans", fontSize=8.8, leading=12, textColor=ENCRE),
}


def tampon(c, x, y, val):
    """Tampon circulaire « Validé par Sami al Athary »."""
    c.saveState()
    c.setStrokeColor(colors.HexColor(OR)); c.setFillColor(colors.HexColor(OR))
    c.setLineWidth(1.6); c.circle(x, y, 17 * mm)
    c.setLineWidth(.6); c.circle(x, y, 14.8 * mm)
    c.setFont("Sans-B", 8); c.drawCentredString(x, y + 4 * mm, "VALIDÉ PAR")
    c.setFont("Serif-B", 9.5); c.drawCentredString(x, y - .5 * mm, "Sami al Athary")
    c.setFont("Sans", 7); c.drawCentredString(x, y - 5 * mm, val.get("date", ""))
    c.restoreState()


def construire(ep_id):
    eps = json.loads((DATA / "episodes.json").read_text(encoding="utf-8"))
    ep = next(e for e in eps if e["id"] == ep_id)
    series = {s["id"]: s for s in json.loads((DATA / "series.json").read_text(encoding="utf-8"))["series"]}
    serie = series[ep["serie"]]
    tr = json.loads((DATA / "transcriptions" / f"{ep_id}.json").read_text(encoding="utf-8"))
    val_f = DATA / "validations.json"
    validation = (json.loads(val_f.read_text(encoding="utf-8")) if val_f.exists() else {}).get(str(ep_id))
    segs, duree = tr["segments"], tr["duree"]
    blocs = parties(segs)
    texte_fr = " ".join(s["texte"] for s in segs if not s["arabe"])
    mc = mots_cles(texte_fr)

    tmp = DATA / "pdf" / "_img"
    tmp.mkdir(parents=True, exist_ok=True)
    fig_serie(ep, [e for e in eps if e["serie"] == ep["serie"]], tmp / "serie.png")
    fig_deroule(segs, blocs, duree, tmp / "deroule.png")
    fig_mots(mc, tmp / "mots.png")

    sortie = DATA / "pdf" / f"{ep_id}.pdf"
    doc = SimpleDocTemplate(str(sortie), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=24 * mm, bottomMargin=18 * mm,
                            title=f"{serie['nom']} n° {ep['num']}", author="Sami al Athary")
    titre_cours = ESSENTIEL(ep["titre"]) or (f"Cours n° {ep['num']}" if ep["num"] is not None else serie["nom"])
    h = []
    logo = RACINE / "icons" / "logo.png"
    if logo.exists():
        h += [Image(str(logo), width=26 * mm, height=26 * mm), Spacer(1, 3 * mm)]
    h += [Paragraph(ESSENTIEL(serie["nom"]), S["titre"]),
          Paragraph(f"Cours n° {ep['num']}" + (f" · {ESSENTIEL(ep['titre'])}" if ep["titre"] else "") if ep["num"] is not None else titre_cours, S["sous"])]

    fiche = [["Enseignant", "Sami al Athary"],
             ["Livre étudié", ESSENTIEL(serie.get("auteur") and f"{serie['nom']} — {serie['auteur']}" or serie["nom"])],
             ["Date", ep.get("date") or "—"], ["Durée", hms(duree)],
             ["Écouter", ep["audio"]]]
    t = Table([[Paragraph(a, S["petit"]), Paragraph(b, S["mention"])] for a, b in fiche], colWidths=[30 * mm, 140 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(OR_CLAIR)), ("BOX", (0, 0), (-1, -1), .6, colors.HexColor(OR)),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                           ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
    h += [t, Spacer(1, 4 * mm)]

    if validation:
        mention = f"<b>Contenu relu et validé par Sami al Athary</b> le {validation.get('date', '')}."
        fond = "#E7F2EA"
    else:
        mention = ("<b>Transcription automatique, sans contrôle de Sami al Athary.</b> Ce document n'a pas été relu par "
                   "l'enseignant et peut contenir des erreurs. Les passages en arabe (versets, hadiths, citations) ne sont "
                   "volontairement pas retranscrits : pour eux, reportez-vous à l'audio. En cas de doute, l'audio fait foi.")
        fond = "#FBF3E3"
    m = Table([[Paragraph(mention, S["mention"])]], colWidths=[170 * mm])
    m.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fond)), ("BOX", (0, 0), (-1, -1), .6, colors.HexColor(OR)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    h += [m, Spacer(1, 2 * mm)]

    h += [Paragraph("Place du cours dans la série", S["h2"]), Image(str(tmp / "serie.png"), width=170 * mm, height=29 * mm)]
    part_ar = sum(s["fin"] - s["debut"] for s in segs if s["arabe"]) / max(duree, 1)
    h += [KeepTogether([Paragraph("Déroulé du cours", S["h2"]),
                        Paragraph(f"{len(blocs)} parties · environ {round(part_ar * 100)} % du temps en arabe (lectures, versets, hadiths).", S["petit"]),
                        Image(str(tmp / "deroule.png"), width=170 * mm, height=40 * mm)])]
    sommaire = [[Paragraph(f"<b>{i}</b>", S["mention"]), Paragraph(hms(b[0]["debut"]), S["petit"]),
                 Paragraph(", ".join(m for m, _ in mots_cles(" ".join(s["texte"] for s in b), 3)) or "passage en arabe", S["mention"])]
                for i, b in enumerate(blocs, 1)]
    st = Table([[Paragraph("<b>Partie</b>", S["petit"]), Paragraph("<b>Début</b>", S["petit"]), Paragraph("<b>Thèmes repérés</b>", S["petit"])]] + sommaire,
               colWidths=[16 * mm, 20 * mm, 134 * mm])
    st.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), .8, colors.HexColor(OR)), ("LINEBELOW", (0, 1), (-1, -1), .3, colors.HexColor("#DDDDDD")),
                            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    h += [Spacer(1, 2 * mm), st]
    h += [KeepTogether([Paragraph("Mots les plus présents", S["h2"]), Image(str(tmp / "mots.png"), width=170 * mm, height=69 * mm)])]

    h += [PageBreak(), Paragraph("Le cours", S["h2"])]
    for i, b in enumerate(blocs, 1):
        cles = ", ".join(m for m, _ in mots_cles(" ".join(s["texte"] for s in b), 3))
        h.append(Paragraph(f"Partie {i} · {hms(b[0]['debut'])}" + (f" — {cles}" if cles else ""), S["h3"]))
        para, prec_fin = [], None
        for s in b:
            if s["arabe"]:
                if para:
                    h.append(Paragraph(" ".join(para), S["corps"])); para = []
                h.append(Paragraph(f"[Passage en arabe non retranscrit · {hms(s['debut'])} – {hms(s['fin'])}]", S["ar"]))
            else:
                if para and prec_fin is not None and s["debut"] - prec_fin > 1.5 and len(" ".join(para)) > 350:
                    h.append(Paragraph(" ".join(para), S["corps"])); para = []
                para.append(s["texte"].replace("&", "&amp;").replace("<", "&lt;"))
                prec_fin = s["fin"]
        if para:
            h.append(Paragraph(" ".join(para), S["corps"]))

    def decor(c, d):
        c.saveState()
        c.setFillColor(colors.HexColor(VERT)); c.rect(0, A4[1] - 12 * mm, A4[0], 12 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor(OR)); c.rect(0, A4[1] - 12.8 * mm, A4[0], .8 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("Serif-B", 10); c.drawString(20 * mm, A4[1] - 7.8 * mm, "Sami al Athary")
        c.setFont("Sans", 8); c.drawRightString(A4[0] - 20 * mm, A4[1] - 7.8 * mm, f"{ESSENTIEL(serie['nom'])[:60]} · n° {ep['num']}")
        c.setFillColor(colors.HexColor(GRIS)); c.setFont("Sans", 7.5)
        pied = "Validé par Sami al Athary" if validation else "Transcription automatique · sans contrôle de Sami al Athary · l'audio fait foi"
        c.drawString(20 * mm, 10 * mm, pied); c.drawRightString(A4[0] - 20 * mm, 10 * mm, f"Page {d.page}")
        if validation and d.page == 1:
            tampon(c, A4[0] - 36 * mm, A4[1] - 33 * mm, validation)
        c.restoreState()

    doc.build(h, onFirstPage=decor, onLaterPages=decor)
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    liste = DATA / "pdfs.json"
    ids = set(json.loads(liste.read_text(encoding="utf-8"))) if liste.exists() else set()
    ids.add(ep_id)
    liste.write_text(json.dumps(sorted(ids)), encoding="utf-8")
    print("PDF :", sortie)


if __name__ == "__main__":
    for i in sys.argv[1:]:
        construire(int(i))
