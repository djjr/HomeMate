// Service worker: caches the app's own files so it opens instantly.
// API calls always go to the network, because cached device state would be wrong.

const CACHE = "homemate-v1";
const SHELL = ["/", "/index.html", "/style.css", "/app.js", "/icon.svg", "/manifest.webmanifest"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
});

self.addEventListener("activate", (event) => {
  // Delete caches from older versions (bump CACHE when the files change).
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))),
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api/")) return; // let the browser handle it normally
  // Network first, cache as fallback: you get updates when online.
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
