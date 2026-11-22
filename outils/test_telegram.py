"""Diagnostic du robot Telegram, sans rien publier : vérifie la clé et les droits sur le canal."""
import json
import os
import re
import urllib.parse
import urllib.request

CANAL = "@Sami_Athary"
jeton = os.environ.get("TELEGRAM_BOT_TOKEN", "")
print("Clé présente :", bool(jeton.strip()))
print("Longueur :", len(jeton), "| espaces ou retours à la ligne :", bool(re.search(r"\s", jeton)))
print("Forme attendue (chiffres:lettres) :", bool(re.fullmatch(r"\d+:[\w-]{30,}", jeton.strip())))
jeton = jeton.strip()


def appel(methode, **p):
    url = f"https://api.telegram.org/bot{jeton}/{methode}?" + urllib.parse.urlencode(p)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")
    except Exception as e:
        return {"ok": False, "description": str(e).replace(jeton, "***")}


moi = appel("getMe")
print("Robot :", moi.get("result", {}).get("username") if moi.get("ok") else moi.get("description"))
if moi.get("ok"):
    m = appel("getChatMember", chat_id=CANAL, user_id=moi["result"]["id"])
    if m.get("ok"):
        r = m["result"]
        print("Statut sur le canal :", r.get("status"), "| peut publier :", r.get("can_post_messages"))
    else:
        print("Canal :", m.get("description"))
