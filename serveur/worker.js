// Petit serveur de l'appli : vérifie les codes de Sami et d'Eyoub, garde l'annonce affichée sur l'accueil.
// Les codes ne sont jamais dans le code de l'appli : ils sont stockés comme secrets (CODE_SAMI, CODE_EYOUB).

const ORIGINES = ["https://eyoubbouarfa.github.io"];
const DUREE_JETON = 1000 * 60 * 60 * 24 * 365; // une connexion dure un an sur le téléphone

function cors(req) {
  const o = req.headers.get("Origin") || "";
  return {
    "Access-Control-Allow-Origin": ORIGINES.includes(o) ? o : ORIGINES[0],
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Vary": "Origin",
  };
}
const json = (req, data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json; charset=utf-8", ...cors(req) } });

async function hmac(cle, texte) {
  const k = await crypto.subtle.importKey("raw", new TextEncoder().encode(cle), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", k, new TextEncoder().encode(texte));
  return btoa(String.fromCharCode(...new Uint8Array(sig))).replace(/[+/=]/g, c => ({ "+": "-", "/": "_", "=": "" }[c]));
}
const egal = (a, b) => { // comparaison à temps constant
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let r = 0; for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i); return r === 0;
};
const cleSignature = env => `${env.CODE_SAMI}|${env.CODE_EYOUB}|reflexions`;

// Droits : Sami a tout, Eyoub seulement les annonces
const DROITS = { Sami: ["annonce", "cours"], Eyoub: ["annonce"] };
const peut = (qui, droit) => !!qui && (DROITS[qui] || []).includes(droit);

async function creerJeton(env, qui) {
  const fin = Date.now() + DUREE_JETON;
  return `${qui}.${fin}.${await hmac(cleSignature(env), `${qui}.${fin}`)}`;
}
async function lireJeton(env, req) {
  const j = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/, "");
  const [qui, fin, sig] = j.split(".");
  if (!qui || !fin || !sig || Date.now() > +fin) return null;
  return egal(sig, await hmac(cleSignature(env), `${qui}.${fin}`)) ? qui : null;
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (req.method === "OPTIONS") return new Response(null, { headers: cors(req) });

    // Annonce publique
    if (url.pathname === "/annonce" && req.method === "GET") {
      const a = await env.KV.get("annonce", "json");
      if (!a || (a.fin && Date.now() > Date.parse(a.fin + "T23:59:59+01:00"))) return json(req, { annonce: null });
      return json(req, { annonce: a });
    }

    // Connexion avec un code
    if (url.pathname === "/connexion" && req.method === "POST") {
      const ip = req.headers.get("CF-Connecting-IP") || "?";
      const cleEssais = `essais:${ip}`;
      const essais = +(await env.KV.get(cleEssais) || 0);
      if (essais >= 8) return json(req, { ok: false, erreur: "Trop d'essais. Réessaie dans un quart d'heure." }, 429);
      let code = "";
      try { code = String((await req.json()).code || "").trim().toLowerCase(); } catch (e) {}
      const qui = egal(code, String(env.CODE_SAMI || "").trim().toLowerCase()) ? "Sami"
                : egal(code, String(env.CODE_EYOUB || "").trim().toLowerCase()) ? "Eyoub" : null;
      if (!qui) {
        await env.KV.put(cleEssais, String(essais + 1), { expirationTtl: 900 });
        return json(req, { ok: false });
      }
      return json(req, { ok: true, qui, droits: DROITS[qui], jeton: await creerJeton(env, qui) });
    }

    // Publier ou retirer l'annonce (réservé)
    if (url.pathname === "/annonce" && (req.method === "POST" || req.method === "DELETE")) {
      const qui = await lireJeton(env, req);
      if (!qui) return json(req, { ok: false, erreur: "Accès refusé" }, 401);
      if (!peut(qui, "annonce")) return json(req, { ok: false, erreur: "Droit insuffisant" }, 403);
      if (req.method === "DELETE") { await env.KV.delete("annonce"); return json(req, { ok: true }); }
      let corps = {};
      try { corps = await req.json(); } catch (e) {}
      const texte = String(corps.texte || "").trim().slice(0, 500);
      if (!texte) return json(req, { ok: false, erreur: "Annonce vide" }, 400);
      const fin = /^\d{4}-\d{2}-\d{2}$/.test(corps.fin || "") ? corps.fin : null;
      const a = { texte, fin, par: qui, date: new Date().toISOString() };
      await env.KV.put("annonce", JSON.stringify(a));
      return json(req, { ok: true, annonce: a });
    }

    return json(req, { ok: true, service: "Réflexions · Sami al Athary" });
  },
};
