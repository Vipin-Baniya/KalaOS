/* ============================================================
   KalaOS Service Worker — offline-first Studio shell
   ============================================================ */

// Bumped from v1 → v2: the fetch handler below now uses a static-asset
// allowlist instead of an API-prefix blocklist (see the fetch listener).
// Bumping the name forces activate() to delete the old "kalaos-v1"
// cache bucket outright, purging any token-bearing API responses that
// were cached under the previous, incomplete blocklist logic.
const CACHE_NAME = "kalaos-v2";

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

/* ── Fetch: cache-first only for the known static app-shell assets;
   network-only (never cached) for everything else ──

   Previously this used a blocklist of known backend path prefixes
   (/auth/, /deep-analysis, etc.) and cache-first'd anything that didn't
   match. That list didn't cover every backend route — endpoints like
   /projects, /messages, /conversations, /notifications, and /jobs (which
   pass the session token as a query parameter, per this app's auth
   convention) fell through to the cache-first branch, so their
   responses — and the token embedded in the cached request URL — were
   written to Cache Storage and persisted after logout.

   Flipping to an allowlist of the precached shell files removes that
   gap: only files this service worker explicitly precached (or a
   handful of common static-asset extensions) are ever cache-first'd or
   written to the cache. Every other same-origin or cross-origin
   request — including any current or future backend route — goes
   straight to the network and is never cached. */

const STATIC_ASSET_EXTENSIONS = /\.(css|js|json|svg|png|jpg|jpeg|gif|ico|woff2?|ttf)$/;

function isPrecachedShellAsset(url) {
  const path = "./" + url.pathname.replace(/^\/+/, "");
  return (
    PRECACHE.includes(path) ||
    PRECACHE.includes(url.pathname) ||
    url.pathname === "/" ||
    STATIC_ASSET_EXTENSIONS.test(url.pathname)
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method === "GET" && url.origin === self.location.origin && isPrecachedShellAsset(url)) {
    // App shell / static assets — cache-first with background refresh.
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
    return;
  }

  // Everything else (all backend/API calls) — network-only, never cached.
  event.respondWith(
    fetch(request).catch(() =>
      new Response(JSON.stringify({ detail: "You appear to be offline." }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      })
    )
  );
});
