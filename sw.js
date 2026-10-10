'use strict';
const VERSION = '4.4.2';
const CACHE = 'fart-machine-v' + VERSION;
const SOUND_IDS = ['smygaren','kanonen','blota','trumpeten','ankan','vulkanen','snabbisen','raketen','katastrofen'];
const SONG_IDS = ['blinka-lilla-stjarna','ba-ba-vita-lamm','broder-jakob','imse-vimse-spindel','bjornen-sover','baby-shark'];
const ASSETS = ['./','./index.html','./app-v4.4.js','./theme-v4.css','./manifest.webmanifest','./icon.svg',...SOUND_IDS.map(id => './audio/' + id + '.mp3'),...SONG_IDS.map(id => './audio/songs/' + id + '.mp3'),...Array.from({length: 9}, (_, i) => './photos/photo-' + String(i+1).padStart(2, '0') + '.webp')];
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    try {
      const cache = await caches.open(CACHE);
      await cache.addAll(ASSETS.map(url => new Request(url, {cache: 'reload'})));
      const page = await cache.match('./index.html');
      if (!(await page.text()).includes('Version ' + VERSION)) throw new Error('Older app shell returned by host');
      const code = await cache.match('./app-v4.4.js');
      if (!(await code.text()).includes("const VERSION = '" + VERSION + "'")) throw new Error('Older app code returned by host');
      await self.skipWaiting();
    } catch (error) {
      await caches.delete(CACHE);
      throw error;
    }
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(name => name.startsWith('fart-machine-v') && name !== CACHE).map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});
// The main player uses full local Blobs. Native test controls also need HTTP byte ranges.
async function audioRange(cached, range) {
  const match = /^bytes=(\d*)-(\d*)$/.exec(range);
  if (!match || (!match[1] && !match[2])) return cached;
  const data = await cached.arrayBuffer();
  const length = data.byteLength;
  const start = match[1] ? Number(match[1]) : Math.max(0, length - Number(match[2]));
  const end = match[1] && match[2] ? Math.min(length - 1, Number(match[2])) : length - 1;
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start >= length || start > end) {
    return new Response(null, {status: 416, headers: {'Content-Range': 'bytes */' + length}});
  }
  return new Response(data.slice(start, end + 1), {status: 206, headers: {
    'Content-Type': 'audio/mpeg',
    'Content-Length': String(end - start + 1),
    'Content-Range': 'bytes ' + start + '-' + end + '/' + length,
    'Accept-Ranges': 'bytes'
  }});
}
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || !url.href.startsWith(self.registration.scope)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const scope = new URL(self.registration.scope);
    if (event.request.mode === 'navigate' && (url.pathname === scope.pathname || url.pathname === scope.pathname + 'index.html')) {
      return (await cache.match('./index.html')) || fetch(event.request);
    }
    const cached = await cache.match(event.request);
    if (!cached) return fetch(event.request);
    const range = event.request.headers.get('Range');
    if (range && url.pathname.endsWith('.mp3')) return audioRange(cached, range);
    return cached;
  })());
});
self.addEventListener('message', event => {
  if (event.data?.type !== 'CACHE_STATUS' || !event.ports[0]) return;
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    const responses = await Promise.all(ASSETS.map(url => cache.match(url)));
    event.ports[0].postMessage({version: VERSION, ready: responses.every(Boolean), sounds: SOUND_IDS.length, songs: SONG_IDS.length});
  })());
});
