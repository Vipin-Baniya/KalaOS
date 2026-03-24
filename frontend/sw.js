/* ============================================================
   KalaOS Service Worker — offline-first Studio shell
   ============================================================ */

const CACHE_NAME = "kalaos-v1";

const PRECACHE = [
  "./",
  "./index.html",
  "./style.css",
  "./app.js",
  "./manifest.json",
  "./icon.svg",
];

/* ── Install: pre-cache the app shell ── */
self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
  );
});

/* ── Activate: remove stale caches ── */
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

/* ── Fetch: network-first for API, cache-first for app shell ── */
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API calls (any path that hits the backend port or known API prefixes)
  const isApiCall =
    url.port === "8000" ||
    url.pathname.startsWith("/auth/") ||
    url.pathname.startsWith("/deep-analysis") ||
    url.pathname.startsWith("/analyze-art") ||
    url.pathname.startsWith("/suggest") ||
    url.pathname.startsWith("/models");

  if (isApiCall) {
    event.respondWith(
      fetch(request).catch(() =>
        new Response(JSON.stringify({ detail: "You appear to be offline." }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        })
      )
    );
    return;
  }

  // App shell — cache-first with background refresh
  event.respondWith(
    caches.match(request).then((cached) => {
      const networkFetch = fetch(request).then((resp) => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then((c) => c.put(request, clone));
        }
        return resp;
      });
      return cached || networkFetch;
    })
  );
});
