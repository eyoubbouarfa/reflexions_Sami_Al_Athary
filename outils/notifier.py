"""Envoie les notifications de l'appli : nouveaux cours (enregistrés ou publiés) et annonces.

Lancé toutes les 10 minutes par .github/workflows/notifier.yml. Le serveur garde les abonnements
et la liste de ce qui a déjà été envoyé ; ce robot compare, envoie ce qui est nouveau, et retire
les téléphones désabonnés. Au tout premier passage, rien n'est envoyé : l'existant est marqué comme déjà vu.
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from recevoir import appel, APPLI  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
MAX_PAR_PASSAGE = 3  # au-delà, un seul message récapitulatif


def evenements():
    """Tout ce qui pourrait mériter une notification, avec une clé unique."""
    ev = []
    a = json.loads(appel("/annonce")).get("annonce")
    if a:
        cle = "n:" + hashlib.sha1((a["texte"] + a["date"]).encode()).hexdigest()[:12]
        ev.append({"cle": cle, "titre": "Annonce · Sami al Athary", "corps": a["texte"], "url": APPLI + "#accueil"})
    for c in json.loads(appel("/cours/attente"))["cours"]:
        if c.get("complet"):
            ev.append({"cle": "a:" + c["id"], "titre": "Nouveau cours", "corps": c.get("titre") or "Cours", "url": f"{APPLI}#nouveau-{c['id']}"})
    series = {s["id"]: s for s in json.loads((RACINE / "data" / "series.json").read_text(encoding="utf-8"))["series"]}
    limite = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
    for e in json.loads((RACINE / "data" / "episodes.json").read_text(encoding="utf-8")):
        if (e.get("date") or "") < limite:
            continue
        s = series.get(e["serie"], {})
        preche = s.get("type") == "preche"
        tete = "Prêche du vendredi" if preche else (s.get("nom") or "Nouveau cours")
        num = f" · n° {e['num']}" if e.get("num") is not None and not preche else ""
        ev.append({"cle": "e:" + str(e["id"]), "titre": tete + num, "corps": e.get("titre") or s.get("nom") or "Cours",
                   "url": f"{APPLI}#ep-{e['id']}", "audio": e.get("audio") if e.get("source") == "appli" else None})
    return ev


def main():
    from pywebpush import webpush, WebPushException

    etat = json.loads(appel("/notif/robot"))
    deja = etat.get("deja")
    ev = evenements()
    if deja is None:  # premier passage : on ne réveille personne avec l'existant
        appel("/notif/robot", "POST", {"deja": [x["cle"] for x in ev]})
        print("Premier passage : existant marqué comme déjà vu.")
        return
    vus = set(deja)
    a_envoyer = []
    for x in ev:
        if x["cle"] in vus:
            continue
        vus.add(x["cle"]); deja.append(x["cle"])
        # un cours enregistré dans l'appli déjà annoncé quand il était en attente n'est pas annoncé une 2e fois
        if x.get("audio") and any(k.startswith("a:") and x["audio"].endswith(f"-{k[2:][-6:]}.mp3") for k in vus):
            continue
        a_envoyer.append(x)
    if len(a_envoyer) > MAX_PAR_PASSAGE:
        annonces = [x for x in a_envoyer if x["cle"].startswith("n:")]
        cours = [x for x in a_envoyer if not x["cle"].startswith("n:")]
        a_envoyer = annonces + [{"titre": f"{len(cours)} nouveaux cours", "corps": " · ".join(x["corps"] for x in cours[:4]), "url": APPLI + "#accueil"}]
    morts = []
    v = etat["vapid"]
    for x in a_envoyer:
        donnees = json.dumps({"titre": x["titre"], "corps": x["corps"][:300], "url": x["url"]}, ensure_ascii=False)
        ok = 0
        for ab in etat["abonnes"]:
            if ab["cle"] in morts:
                continue
            try:
                webpush(subscription_info=ab["abo"], data=donnees, vapid_private_key=v["d"],
                        vapid_claims={"sub": "mailto:eyoubbouarfa@users.noreply.github.com"}, ttl=86400, timeout=20)
                ok += 1
            except WebPushException as e:
                code = getattr(e.response, "status_code", None)
                if code in (404, 410):
                    morts.append(ab["cle"])
                else:
                    print("Échec d'envoi :", code, str(e)[:150])
            except Exception as e:  # un téléphone injoignable ne bloque pas les autres
                print("Échec d'envoi :", str(e)[:150])
        print(f"Envoyé à {ok} téléphone(s) : {x['titre']} — {x['corps'][:60]}")
    appel("/notif/robot", "POST", {"deja": deja, "morts": morts})
    if not a_envoyer:
        print("Rien de nouveau.")
    if morts:
        print(f"{len(morts)} téléphone(s) désabonné(s) retiré(s).")


if __name__ == "__main__":
    main()
