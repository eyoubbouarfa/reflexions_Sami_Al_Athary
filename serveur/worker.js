// Petit serveur de l'appli : vérifie les codes de Sami et d'Eyoub, garde l'annonce affichée sur l'accueil.
// Les codes ne sont jamais dans le code de l'appli : ils sont stockés comme secrets (CODE_SAMI, CODE_EYOUB).

const ORIGINES = ["https://eyoubbouarfa.github.io"];
const DUREE_JETON = 1000 * 60 * 60 * 24 * 365; // une connexion dure un an sur le téléphone

function cors(req) {
  const o = req.headers.get("Origin") || "";
  return {
    "Access-Control-Allow-Origin": ORIGINES.includes(o) ? o : ORIGINES[0],
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, Range, X-Robot",
    "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges, Content-Length",
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

// ---------- Enregistrements de Sami ----------
// Chaque cours enregistré est envoyé en parties (une par reprise d'enregistrement) et gardé ici
// le temps que le robot GitHub le convertisse en mp3 et le range pour de bon. Il est écoutable tout de suite.
const DEPOT = "eyoubbouarfa/savoir_Sami_Al_Athary";
const ETIQUETTE = "cours"; // audios enregistrés, PDF et transcriptions, tous au même endroit
const MAX_PARTIE = 24 * 1024 * 1024; // limite d'une valeur KV : 25 Mo
const ID_OK = /^[a-z0-9-]{6,40}$/;
const cleRobot = env => hmac(String(env.CODE_SAMI || ""), "robot");
async function estRobot(env, req) { return egal(req.headers.get("X-Robot") || "", await cleRobot(env)); }

function reponseAudio(req, buf, type) {
  const total = buf.byteLength, r = /bytes=(\d*)-(\d*)/.exec(req.headers.get("Range") || "");
  const base = { "Content-Type": type, "Accept-Ranges": "bytes", "Cache-Control": "public, max-age=3600", ...cors(req) };
  if (!r) return new Response(buf, { headers: { ...base, "Content-Length": String(total) } });
  let debut = r[1] === "" ? Math.max(0, total - +r[2]) : +r[1];
  let fin = r[1] === "" || r[2] === "" ? total - 1 : Math.min(+r[2], total - 1);
  if (debut > fin || debut >= total) return new Response(null, { status: 416, headers: { ...base, "Content-Range": `bytes */${total}` } });
  return new Response(buf.slice(debut, fin + 1), { status: 206, headers: { ...base, "Content-Length": String(fin - debut + 1), "Content-Range": `bytes ${debut}-${fin}/${total}` } });
}

async function enAttente(env) {
  const parId = {};
  let curseur;
  do {
    const l = await env.KV.list({ prefix: "cours:", cursor: curseur });
    for (const k of l.keys) {
      const [, id, n] = k.name.split(":"), m = k.metadata || {};
      const c = parId[id] ||= { id, titre: m.titre || "", date: m.date || "", type: m.type || "", parties: [], complet: false };
      c.parties.push(+n); if (m.dernier) c.complet = true; if (m.titre) c.titre = m.titre;
    }
    curseur = l.list_complete ? null : l.cursor;
  } while (curseur);
  return Object.values(parId).map(c => ({ ...c, parties: c.parties.sort((a, b) => a - b) })).sort((a, b) => b.date.localeCompare(a.date));
}

async function routesCours(req, env, url) {
  const p = url.pathname;
  // Liste publique des cours enregistrés pas encore rangés
  if (p === "/cours/attente" && req.method === "GET") return json(req, { cours: await enAttente(env) });

  // Écoute d'une partie encore en attente
  let m = /^\/cours\/partie\/([a-z0-9-]+)\/(\d+)$/.exec(p);
  if (m && (req.method === "GET" || req.method === "HEAD")) {
    const v = await env.KV.getWithMetadata(`cours:${m[1]}:${m[2].padStart(3, "0")}`, "arrayBuffer");
    if (!v.value) return json(req, { ok: false }, 404);
    return reponseAudio(req, v.value, (v.metadata && v.metadata.type) || "audio/mp4");
  }

  // Dépôt d'une partie (Sami)
  if (p === "/cours/partie" && req.method === "POST") {
    const qui = await lireJeton(env, req);
    if (!qui) return json(req, { ok: false, erreur: "Accès refusé" }, 401);
    if (!peut(qui, "cours")) return json(req, { ok: false, erreur: "Droit insuffisant" }, 403);
    const id = url.searchParams.get("id") || "", n = +(url.searchParams.get("n") || 0);
    if (!ID_OK.test(id) || !(n >= 0 && n < 1000)) return json(req, { ok: false, erreur: "Paramètres invalides" }, 400);
    const buf = await req.arrayBuffer();
    if (!buf.byteLength) return json(req, { ok: false, erreur: "Fichier vide" }, 400);
    if (buf.byteLength > MAX_PARTIE) return json(req, { ok: false, erreur: "Partie trop lourde (24 Mo max)" }, 413);
    const meta = {
      titre: (url.searchParams.get("titre") || "").trim().slice(0, 300),
      type: (req.headers.get("Content-Type") || "audio/mp4").split(";")[0].slice(0, 40),
      date: url.searchParams.get("date") || new Date().toISOString(),
      dernier: url.searchParams.get("dernier") === "1", taille: buf.byteLength, par: qui,
    };
    await env.KV.put(`cours:${id}:${String(n).padStart(3, "0")}`, buf, { metadata: meta });
    return json(req, { ok: true, id, n, taille: buf.byteLength });
  }

  // Suppression d'un cours en attente (robot après rangement, ou Sami)
  m = /^\/cours\/([a-z0-9-]+)$/.exec(p);
  if (m && req.method === "DELETE") {
    const qui = await lireJeton(env, req);
    if (!(await estRobot(env, req)) && !peut(qui, "cours")) return json(req, { ok: false, erreur: "Accès refusé" }, 401);
    const l = await env.KV.list({ prefix: `cours:${m[1]}:` });
    await Promise.all(l.keys.map(k => env.KV.delete(k.name)));
    return json(req, { ok: true, supprimees: l.keys.length });
  }

  // Alertes pour Sami (ex. copie Telegram ratée) : déposées par le robot, lues et effacées par Sami
  if (p === "/alertes") {
    if (req.method === "POST") {
      if (!(await estRobot(env, req))) return json(req, { ok: false }, 401);
      let a = {}; try { a = await req.json(); } catch (e) {}
      const liste = (await env.KV.get("alertes", "json")) || [];
      liste.unshift({ texte: String(a.texte || "").slice(0, 500), date: new Date().toISOString() });
      await env.KV.put("alertes", JSON.stringify(liste.slice(0, 30)));
      return json(req, { ok: true });
    }
    const qui = await lireJeton(env, req);
    if (!peut(qui, "cours")) return json(req, { ok: false, erreur: "Accès refusé" }, 401);
    if (req.method === "DELETE") { await env.KV.delete("alertes"); return json(req, { ok: true }); }
    return json(req, { alertes: (await env.KV.get("alertes", "json")) || [] });
  }

  // Écoute d'un cours rangé : relaie le mp3 stocké sur GitHub avec le bon type pour les téléphones
  m = /^\/(audio|pdf)\/([\w.-]+\.(mp3|pdf))$/.exec(p);
  if (m && (req.method === "GET" || req.method === "HEAD")) {
    const fichier = m[2], estPdf = m[3] === "pdf";
    const h = new Headers();
    if (req.headers.get("Range")) h.set("Range", req.headers.get("Range"));
    const r = await fetch(`https://github.com/${DEPOT}/releases/download/${ETIQUETTE}/${fichier}`, { headers: h, redirect: "follow", method: req.method });
    const out = new Headers(cors(req));
    for (const k of ["Content-Length", "Content-Range", "Accept-Ranges", "ETag", "Last-Modified"]) if (r.headers.get(k)) out.set(k, r.headers.get(k));
    out.set("Content-Type", estPdf ? "application/pdf" : "audio/mpeg");
    if (estPdf) out.set("Content-Disposition", `inline; filename="${fichier}"`); out.set("Accept-Ranges", "bytes"); out.set("Cache-Control", "public, max-age=86400");
    return new Response(r.body, { status: r.status, headers: out });
  }
  return null;
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (req.method === "OPTIONS") return new Response(null, { headers: cors(req) });

    if (url.pathname.startsWith("/cours") || url.pathname.startsWith("/audio/") || url.pathname.startsWith("/pdf/") || url.pathname === "/alertes") {
      const r = await routesCours(req, env, url);
      if (r) return r;
    }

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

    return json(req, { ok: true, service: "Savoir · Sami al Athary" });
  },
};
