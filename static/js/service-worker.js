var CACHE_VERSION = 'sharemint-v1';
var PRECACHE_URLS = [
    '/static/css/main.css',
    '/static/js/main.js',
    '/static/js/flash-messages.js',
    '/static/js/numeric_input.js',
    '/static/images/logo192.png',
    '/static/images/logo512.png',
    '/auth/login/',
];

self.addEventListener('install', function (event) {
    event.waitUntil(
        caches.open(CACHE_VERSION).then(function (cache) {
            return cache.addAll(PRECACHE_URLS);
        }).then(function () {
            return self.skipWaiting();
        })
    );
});

self.addEventListener('activate', function (event) {
    event.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(
                keys.filter(function (key) { return key !== CACHE_VERSION; })
                    .map(function (key) { return caches.delete(key); })
            );
        }).then(function () {
            return self.clients.claim();
        })
    );
});

self.addEventListener('fetch', function (event) {
    var request = event.request;
    if (request.method !== 'GET') return;

    var url = new URL(request.url);
    if (url.origin !== self.location.origin) return;

    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request).catch(function () {
                return caches.match('/auth/login/');
            })
        );
        return;
    }

    if (url.pathname.indexOf('/static/') === 0) {
        event.respondWith(
            caches.match(request).then(function (cached) {
                return cached || fetch(request).then(function (response) {
                    if (response && response.status === 200) {
                        var copy = response.clone();
                        caches.open(CACHE_VERSION).then(function (cache) {
                            cache.put(request, copy);
                        });
                    }
                    return response;
                });
            })
        );
    }
});
