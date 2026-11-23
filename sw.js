const CACHE = "sami-cours-v30";
const FICHIERS = ["./", "index.html", "manifest.webmanifest", "icons/logo.png", "icons/icon-192.png", "icons/icon-512.png",
  "data/series.json", "data/episodes.json", "data/config.json", "data/textes.json"];
self.addEventListener("install", e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(FICHIERS)).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(k => Promise.all(k.filter(x => x !== CACHE).map(x => caches.delete(x)))).then(() => self.clients.claim())));
// Réseau d'abord (les nouveaux cours s'affichent tout de suite), cache en secours hors ligne
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  e.respondWith(fetch(e.request, { cache: "no-cache" }).then(res => {
    if (res.ok) { const cp = res.clone(); caches.open(CACHE).then(c => c.put(e.request, cp)); }
    return res;
  }).catch(() => caches.match(e.request).then(r => r || caches.match("index.html"))));
});

// Notifications : nouveaux cours et annonces
self.addEventListener("push", e => {
  let d = {};
  try { d = e.data.json(); } catch (x) { d = { corps: e.data ? e.data.text() : "" }; }
  e.waitUntil(self.registration.showNotification(d.titre || "Sami al Athary", {
    body: d.corps || "", icon: "icons/icon-192.png", badge: "icons/icon-192.png", tag: d.url || "sami", data: { url: d.url || "./" },
  }));
});
self.addEventListener("notificationclick", e => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "./";
  e.waitUntil(clients.matchAll({ type: "window", includeUncontrolled: true }).then(liste => {
    const c = liste.find(x => x.url.startsWith(self.registration.scope));
    if (c) return c.focus().then(() => c.navigate(url)).catch(() => clients.openWindow(url));
    return clients.openWindow(url);
  }));
});
