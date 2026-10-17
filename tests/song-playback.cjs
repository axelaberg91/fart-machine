'use strict';

// Run with: node tests/song-playback.cjs
// For focused song/UI changes: node tests/song-playback.cjs --replacement-only
// For visual-only changes: node tests/song-playback.cjs --design-only
// Uses real browser media, a localhost server, and no production instrumentation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { createHash } = require('node:crypto');
const http = require('node:http');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');

const root = path.resolve(__dirname, '..');
const output = process.env.SONG_TEST_OUTPUT || path.resolve(root, '..', 'qa');
const runtime = process.env.CODEX_NODE_MODULES || path.join(process.env.USERPROFILE || '', '.cache', 'codex-runtimes', 'codex-primary-runtime', 'dependencies', 'node', 'node_modules');
let playwright;
try { playwright = require('playwright'); }
catch (_) { playwright = createRequire(path.join(runtime, 'playwright', 'package.json'))('playwright'); }
const browserPath = process.env.CHROME_PATH || [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
].find(file => fs.existsSync(file));
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.webmanifest': 'application/manifest+json' };
const songSelector = '#songs button[data-song]';
const padSelector = '#grid button[data-sound]';
const replacementOnly = process.argv.includes('--replacement-only');
const designOnly = process.argv.includes('--design-only');
const replacementId = 'through-the-fire-and-flames';
const expectedSongs = [
  {
    "id": "greta-gris",
    "name": "Greta Fis"
  },
  {
    "id": "bjornen-sover",
    "name": "Björnen fiser"
  },
  {
    "id": "baby-shark",
    "name": "Baby Shart"
  },
  {
    "id": "en-livstid-i-krig",
    "name": "En livstid på dass"
  },
  {
    "id": "bromance",
    "name": "Pruttmance"
  },
  {
    "id": "sommartider",
    "name": "Sommargaser"
  },
  {
    "id": "sandstorm",
    "name": "Fartstorm"
  },
  {
    "id": "ring-of-fire",
    "name": "Ring of Farts"
  },
  {
    "id": "the-final-countdown",
    "name": "The Final Fartdown"
  },
  {
    "id": "imperial-march",
    "name": "The Imperial Fart"
  },
  {
    "id": "seven-nation-army",
    "name": "Seven Nation Farty"
  },
  {
    "id": "through-the-fire-and-flames",
    "name": "Through the Fire and Farts"
  }
];
const expectedSongIds = expectedSongs.map(song => song.id);
const expectedCaptions = {
  "greta-gris": "Julian Prutt",
  "bjornen-sover": "Pruttkören",
  "baby-shark": "Stinkfong",
  "en-livstid-i-krig": "Sabatarm",
  "bromance": "Tim Brak (Avifis)",
  "sommartider": "Gyllene Tarmar",
  "sandstorm": "Da Röv",
  "ring-of-fire": "Johnny Gas",
  "the-final-countdown": "Europrutt",
  "imperial-march": "John Windliams",
  "seven-nation-army": "The Brown Stripes",
  "through-the-fire-and-flames": "DragonFjärt"
};
const errors = [];
const reports = [];

function instrument() {
  window.__mediaTest = { calls: [], playing: [], ended: [], webAudio: [] };
  let click = null;
  const nativeListen = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function (type, handler, options) {
    if (type !== 'click' || this.tagName !== 'BUTTON' || typeof handler !== 'function') return nativeListen.call(this, type, handler, options);
    return nativeListen.call(this, type, function (event) {
      const previous = click;
      click = { trusted: event.isTrusted, id: this.dataset.song || this.dataset.sound || this.id };
      try { return handler.call(this, event); }
      finally { click = previous; }
    }, options);
  };
  for (const property of ['AudioContext', 'webkitAudioContext', 'OfflineAudioContext', 'webkitOfflineAudioContext']) {
    Object.defineProperty(window, property, { configurable: true, get() {
      window.__mediaTest.webAudio.push(property);
      throw new Error('Web Audio must not be used for native song playback: ' + property);
    } });
  }
  const nativePlay = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function () {
    const entry = { click: click && { ...click }, src: this.src, volume: this.volume };
    window.__mediaTest.calls.push(entry);
    this.addEventListener('playing', () => window.__mediaTest.playing.push({ src: this.src, duration: this.duration, currentTime: this.currentTime }), { once: true });
    this.addEventListener('ended', () => window.__mediaTest.ended.push(this.src), { once: true });
    const result = nativePlay.call(this);
    if (result) result.then(() => { entry.result = 'resolved'; }, error => { entry.result = error.name; });
    return result;
  };
}

async function check(name, operation, validateReplacement = false, validateDesign = false) {
  if (replacementOnly && !validateReplacement) return;
  if (designOnly && !validateDesign) return;
  try { await operation(); reports.push({ name, ok: true }); console.log('PASS ' + name); }
  catch (error) { errors.push(error); reports.push({ name, ok: false, error: error.message }); console.error('FAIL ' + name + '\n' + error.stack); }
}

async function stop(page) {
  await page.locator('#stop').click();
  await page.waitForFunction(() => document.querySelectorAll('#native-players audio').length === 0);
}

async function playAndWait(page, selector) {
  const before = await page.evaluate(() => window.__mediaTest.playing.length);
  await page.locator(selector).click();
  await page.waitForFunction(count => window.__mediaTest.playing.length > count, before, { timeout: 15000 });
  const state = await page.evaluate(() => ({ call: window.__mediaTest.calls.at(-1), played: window.__mediaTest.playing.at(-1) }));
  assert.equal(state.call.click?.trusted, true, 'play() must be called during a real user click');
  assert.ok(state.call.click.id, 'play() must be called synchronously within the trusted button callback');
  assert.ok(Number.isFinite(state.played.duration) && state.played.duration > 0, 'actual browser decoder must read a nonempty audio recording');
  return state;
}

async function waitForSongIllustrations(page) {
  await page.waitForFunction(() => {
    const icons = [...document.querySelectorAll('#songs .song-icon')];
    return icons.length === 12 && icons.every(icon => {
      const box = icon.getBBox();
      return box.width > 0 && box.height > 0;
    });
  });
}

async function main() {
  fs.mkdirSync(output, { recursive: true });
  for (const name of ['app-v4.4.js', 'sw.js']) new vm.Script(fs.readFileSync(path.join(root, name), 'utf8'), { filename: name });
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /app-v4\.4\.js/);
  assert.match(html, /Version 5\.3/);
  console.log('PASS syntax and version references');

  const server = http.createServer((request, response) => {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const file = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
    if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { response.writeHead(404); response.end(); return; }
    const bytes = fs.readFileSync(file);
    response.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream', 'Content-Length': bytes.length, 'Cache-Control': 'no-cache' });
    response.end(bytes);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const url = 'http://127.0.0.1:' + server.address().port;
  const browser = await playwright.chromium.launch({ headless: true, ...(browserPath ? { executablePath: browserPath } : {}) });
  let context;
  try {
    context = await browser.newContext({ viewport: { width: 1024, height: 1000 } });
    await context.addInitScript(instrument);
    const page = await context.newPage();
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    await page.goto(url);
    await page.waitForFunction(() => document.querySelectorAll('#songs button[data-song]').length === 12);
    const songs = await page.locator(songSelector).evaluateAll(buttons => buttons.map(button => ({ id: button.dataset.song, name: button.querySelector('.name').textContent })));
    const pads = await page.locator(padSelector).evaluateAll(buttons => buttons.map(button => button.dataset.sound));
    const playbackSongs = designOnly ? [] : songs;
    const playbackPads = replacementOnly || designOnly ? [] : pads;
    const metadata = JSON.parse(fs.readFileSync(path.join(root, 'audio', 'songs', 'metadata.json'), 'utf8'));
    async function playSong(song) {
      const state = await playAndWait(page, '[data-song="' + song.id + '"]');
      const expectedDuration = metadata.songs.find(entry => entry.id === song.id)?.validation.duration_seconds;
      assert.ok(Number.isFinite(expectedDuration), song.id + ' must have a validated duration');
      assert.ok(Math.abs(state.played.duration - expectedDuration) < 0.1, song.id + ' native decoded duration must match its validated recording');
      await stop(page);
      assert.equal(await page.locator('[data-song="' + song.id + '"] small').textContent(), expectedCaptions[song.id], 'stopping restores the artist/origin');
    }

    await check('twelve requested songs in order expose artist/origin captions and nine original pads', async () => {
      assert.equal(songs.length, 12);
      assert.equal(new Set(songs.map(song => song.id)).size, 12);
      assert.deepEqual(songs, expectedSongs);
      assert.equal(pads.length, 9);
      for (const song of songs) {
        const button = page.locator('[data-song="' + song.id + '"]');
        assert.equal(await button.getAttribute('aria-pressed'), 'false');
        assert.equal(await button.getAttribute('aria-label'), 'Spela ' + song.name);
        assert.equal(await button.locator('small').textContent(), expectedCaptions[song.id]);
      }
    }, true, true);

    await check('all twelve custom song illustrations resolve to distinct visible SVG symbols', async () => {
      await waitForSongIllustrations(page);
      const icons = await page.locator(songSelector).evaluateAll(buttons => buttons.map(button => {
        const icon = button.querySelector('.song-icon');
        const box = icon.getBoundingClientRect();
        const style = getComputedStyle(icon);
        return { id: button.dataset.song, href: icon.querySelector('use')?.getAttribute('href'), viewBox: icon.getAttribute('viewBox'), visible: style.display !== 'none' && style.visibility === 'visible' && Number(style.opacity) > 0, width: box.width, height: box.height };
      }));
      for (const icon of icons) {
        assert.equal(icon.href, './song-icons.svg#' + icon.id, icon.id + ' selects its own illustration');
        assert.equal(icon.viewBox, '0 0 96 96');
        assert.equal(icon.visible, true, icon.id + ' illustration is visible');
        assert.ok(icon.width >= 32 && icon.height >= 32, icon.id + ' illustration has a usable visible size');
      }
      assert.equal(new Set(icons.map(icon => icon.href)).size, 12, 'all twelve illustrations are distinct');
      const spriteIds = await page.evaluate(async () => {
        const response = await fetch('./song-icons.svg');
        if (!response.ok) throw new Error('Illustration sprite could not load');
        const sprite = new DOMParser().parseFromString(await response.text(), 'image/svg+xml');
        if (sprite.querySelector('parsererror')) throw new Error('Illustration sprite has invalid SVG');
        return [...sprite.querySelectorAll('symbol')].map(symbol => symbol.id);
      });
      assert.deepEqual(spriteIds.sort(), [...expectedSongIds].sort(), 'the sprite contains every song illustration');
    }, true, true);

    await check(replacementOnly ? 'all twelve songs decode and start native playback synchronously from a trusted click' : 'all twenty-one recordings decode and start native playback synchronously from a trusted click', async () => {
      for (const song of playbackSongs) await playSong(song);
      for (const id of playbackPads) { await playAndWait(page, '#grid [data-sound="' + id + '"]'); await stop(page); }
      assert.deepEqual(await page.evaluate(() => window.__mediaTest.webAudio), []);
    }, true);

    if (replacementOnly) await check('songs remain exclusive and same-song toggle stops with orchestra checked', async () => {
      await page.locator('#layer').check();
      await playAndWait(page, '[data-song="' + songs[0].id + '"]');
      const previous = await page.locator('#native-players audio').elementHandle();
      const replacement = songs.find(song => song.id === replacementId);
      await playAndWait(page, '[data-song="' + replacementId + '"]');
      assert.equal(await page.locator('#native-players audio').count(), 1);
      assert.equal(await page.locator(songSelector + '[aria-pressed="true"]').count(), 1);
      assert.deepEqual(await previous.evaluate(audio => ({ connected: audio.isConnected, paused: audio.paused, src: audio.getAttribute('src') })), { connected: false, paused: true, src: null });
      assert.equal(await page.locator('[data-song="' + songs[0].id + '"]').getAttribute('aria-pressed'), 'false');
      assert.equal(await page.locator('[data-song="' + replacementId + '"]').getAttribute('aria-label'), 'Stoppa ' + replacement.name);
      await page.locator('[data-song="' + replacementId + '"]').click();
      assert.equal(await page.locator('#native-players audio').count(), 0);
      assert.equal(await page.locator(songSelector + '[aria-pressed="true"]').count(), 0);
      assert.equal(await page.locator('[data-song="' + replacementId + '"] small').textContent(), expectedCaptions[replacementId]);
      await playAndWait(page, '[data-song="' + replacementId + '"]');
      await playAndWait(page, '[data-song="' + songs[1].id + '"]');
      assert.equal(await page.locator('#native-players audio').count(), 1);
      assert.equal(await page.locator('[data-song="' + replacementId + '"]').getAttribute('aria-pressed'), 'false');
      assert.equal(await page.locator('[data-song="' + replacementId + '"]').getAttribute('aria-label'), 'Spela ' + replacement.name);
      await stop(page);
    }, true);

    await check('every artist/origin caption returns after toggling and stop-all', async () => {
      for (const song of songs) {
        const button = page.locator('[data-song="' + song.id + '"]');
        await playAndWait(page, '[data-song="' + song.id + '"]');
        assert.equal(await button.locator('small').textContent(), 'Tryck för att stoppa');
        await button.click();
        assert.equal(await page.locator('#native-players audio').count(), 0);
        assert.equal(await button.getAttribute('aria-label'), 'Spela ' + song.name);
        assert.equal(await button.locator('small').textContent(), expectedCaptions[song.id]);
        await playAndWait(page, '[data-song="' + song.id + '"]');
        await stop(page);
        assert.equal(await button.locator('small').textContent(), expectedCaptions[song.id]);
      }
    }, true);

    await check('songs stay exclusive while orchestra still layers original pads', async () => {
      await page.locator('#layer').check();
      await playAndWait(page, '#grid [data-sound="trumpeten"]');
      const original = await page.locator('#native-players audio').elementHandle();
      await playAndWait(page, '[data-song="' + songs[0].id + '"]');
      assert.equal(await page.locator('#native-players audio').count(), 2);
      await playAndWait(page, '[data-song="' + songs[1].id + '"]');
      assert.equal(await page.locator('#native-players audio').count(), 2);
      const first = page.locator('[data-song="' + songs[0].id + '"]');
      assert.equal(await first.getAttribute('aria-pressed'), 'false');
      assert.equal(await first.getAttribute('aria-label'), 'Spela ' + songs[0].name);
      const second = page.locator('[data-song="' + songs[1].id + '"]');
      assert.equal(await second.getAttribute('aria-pressed'), 'true');
      assert.equal(await second.getAttribute('aria-label'), 'Stoppa ' + songs[1].name);
      assert.equal(await page.locator(songSelector + '[aria-pressed="true"]').count(), 1);
      assert.deepEqual(await original.evaluate(audio => ({ connected: audio.isConnected, paused: audio.paused })), { connected: true, paused: false });
      await second.click();
      assert.equal(await page.locator('#native-players audio').count(), 1);
      assert.equal(await second.getAttribute('aria-pressed'), 'false');
      assert.equal(await second.getAttribute('aria-label'), 'Spela ' + songs[1].name);
      assert.deepEqual(await original.evaluate(audio => ({ connected: audio.isConnected, paused: audio.paused })), { connected: true, paused: false });
      await playAndWait(page, '#grid [data-sound="vulkanen"]');
      assert.equal(await page.locator('#native-players audio').count(), 2, 'original pads may still overlap with orchestra checked');
      await stop(page);
      assert.equal(await page.locator(songSelector + '[aria-pressed="true"]').count(), 0);
    });

    await check('unchecking orchestra stops current audio and subsequent selections are exclusive', async () => {
      await page.locator('#layer').check();
      await playAndWait(page, '[data-song="' + songs[0].id + '"]');
      await playAndWait(page, '[data-song="' + songs[1].id + '"]');
      await page.locator('#layer').uncheck();
      assert.equal(await page.locator('#native-players audio').count(), 0);
      await playAndWait(page, '[data-song="' + songs[0].id + '"]');
      await playAndWait(page, '[data-song="' + songs[1].id + '"]');
      assert.equal(await page.locator('#native-players audio').count(), 1);
      assert.equal(await page.locator('[data-song="' + songs[0].id + '"]').getAttribute('aria-pressed'), 'false');
      await playAndWait(page, '#grid [data-sound="' + pads[0] + '"]');
      assert.equal(await page.locator('[data-song="' + songs[1].id + '"]').getAttribute('aria-pressed'), 'false');
      await playAndWait(page, '#grid [data-sound="trumpeten"]');
      await playAndWait(page, '#grid [data-sound="vulkanen"]');
      assert.equal(await page.locator('#native-players audio').count(), 1, 'original pads stay exclusive with orchestra unchecked');
      await stop(page);
      await page.locator('#layer').check();
    });

    await check('volume applies to active songs and new original sounds', async () => {
      await playAndWait(page, '[data-song="' + songs[0].id + '"]');
      async function setVolume(value) { await page.locator('#vol').evaluate((slider, next) => { slider.value = String(next); slider.dispatchEvent(new Event('input', { bubbles: true })); }, value); }
      await setVolume(25);
      const quiet = await page.locator('#native-players audio').evaluate(audio => audio.volume);
      await setVolume(75);
      const loud = await page.locator('#native-players audio').evaluate(audio => audio.volume);
      assert.ok(quiet > 0 && Math.abs(loud / quiet - 3) < 1e-6);
      const original = await playAndWait(page, '#grid [data-sound="' + pads[0] + '"]');
      assert.ok(Math.abs(original.call.volume - loud) < 1e-6);
      await setVolume(0);
      const levels = await page.locator('#native-players audio').evaluateAll(audios => audios.map(audio => audio.volume));
      assert.ok(levels.every(level => level === 0));
      await stop(page);
      await setVolume(75);
    });

    await check('hidden document and pagehide clean up active playback and accessible state', async () => {
      await playAndWait(page, '[data-song="' + songs[0].id + '"]');
      await page.evaluate(() => { Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' }); document.dispatchEvent(new Event('visibilitychange')); });
      assert.equal(await page.locator('#native-players audio').count(), 0);
      assert.equal(await page.locator(songSelector + '[aria-pressed="true"]').count(), 0);
      await page.evaluate(() => { delete document.visibilityState; });
      await playAndWait(page, '[data-song="' + songs[0].id + '"]');
      await page.evaluate(() => window.dispatchEvent(new Event('pagehide')));
      assert.equal(await page.locator('#native-players audio').count(), 0);
      assert.equal(await page.locator(songSelector + '[aria-pressed="true"]').count(), 0);
    });

    await check('service worker caches complete version 5.3 shell, twelve songs, and original audio', async () => {
      await page.locator('#offline.ready').waitFor({ timeout: 30000 });
      assert.match(await page.locator('#offline.ready').textContent(), /12\s+låtar/);
      await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller));
      const cache = await page.evaluate(async () => {
        const current = await caches.open('fart-machine-v5.3');
        const keys = await current.keys();
        return Promise.all(keys.map(async request => {
          const response = await current.match(request);
          const data = await response.arrayBuffer();
          const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', data)), byte => byte.toString(16).padStart(2, '0')).join('');
          return { path: new URL(request.url).pathname, status: response.status, bytes: data.byteLength, hash, type: response.headers.get('Content-Type') };
        }));
      });
      assert.ok(cache.some(entry => entry.path === '/app-v4.4.js'));
      assert.ok(cache.some(entry => entry.path === '/song-icons.svg'), 'the new song illustrations are cached');
      assert.equal(cache.length, 37);
      assert.deepEqual(cache.filter(entry => /\/audio\/songs\//.test(entry.path)).map(entry => entry.path).sort(), expectedSongIds.map(id => '/audio/songs/' + id + '.mp3').sort());
      assert.equal(cache.filter(entry => /\/audio\/[^/]+\.mp3$/.test(entry.path)).length, 9);
      for (const entry of cache) {
        assert.equal(entry.status, 200, 'cached assets must be complete, not partial responses');
        const original = fs.readFileSync(path.join(root, entry.path === '/' ? 'index.html' : entry.path.slice(1)));
        assert.equal(entry.bytes, original.length, entry.path + ' cache has the complete response');
        assert.equal(entry.hash, createHash('sha256').update(original).digest('hex'), entry.path + ' cached payload matches the actual file');
        if (entry.path.endsWith('.mp3')) assert.match(entry.type, /audio\/mpeg/);
        if (entry.path.endsWith('.wav')) assert.match(entry.type, /audio\/wav|audio\/x-wav/);
      }
      const status = await page.evaluate(() => new Promise(resolve => { const channel = new MessageChannel(); channel.port1.onmessage = event => resolve(event.data); navigator.serviceWorker.controller.postMessage({ type: 'CACHE_STATUS' }, [channel.port2]); }));
      assert.equal(status.version, '5.3');
      assert.equal(status.ready, true);
      assert.equal(status.sounds, 9);
      assert.equal(status.songs, 12);
    }, true, true);

    await check(designOnly ? 'offline reload, rendered illustrations, and byte range responses work without network' : replacementOnly ? 'offline twelve-song playback restores captions and all twelve byte ranges work without network' : 'offline reload, all song playback, and byte range responses work without network', async () => {
      await context.setOffline(true);
      await page.reload();
      await page.locator('#offline.ready').waitFor({ timeout: 15000 });
      for (const song of playbackSongs) await playSong(song);
      for (const id of playbackPads) { await playAndWait(page, '#grid [data-sound="' + id + '"]'); await stop(page); }
      const paths = await page.evaluate(async () => (await (await caches.open('fart-machine-v5.3')).keys()).map(request => new URL(request.url).pathname).filter(url => url.includes('/audio/songs/')));
      for (const asset of paths) {
        const result = await page.evaluate(async asset => {
          const response = await fetch(asset, { headers: { Range: 'bytes=0-63' } });
          return { status: response.status, type: response.headers.get('Content-Type'), range: response.headers.get('Content-Range'), length: response.headers.get('Content-Length'), bytes: Array.from(new Uint8Array(await response.arrayBuffer())) };
        }, asset);
        const original = fs.readFileSync(path.join(root, asset.slice(1)));
        assert.equal(result.status, 206);
        assert.equal(result.length, '64');
        assert.equal(result.range, 'bytes 0-63/' + original.length);
        assert.match(result.type, asset.endsWith('.wav') ? /audio\/wav|audio\/x-wav/ : /audio\/mpeg/);
        assert.deepEqual(result.bytes, [...original.subarray(0, 64)]);
      }
      const ranges = await page.evaluate(async asset => {
        return Promise.all(['bytes=-32', 'bytes=999999999-', 'bytes=3-2'].map(async range => { const response = await fetch(asset, { headers: { Range: range } }); return { range, status: response.status, bytes: Array.from(new Uint8Array(await response.arrayBuffer())) }; }));
      }, paths[0]);
      assert.equal(ranges[0].status, 206);
      assert.deepEqual(ranges[0].bytes, [...fs.readFileSync(path.join(root, paths[0].slice(1))).subarray(-32)]);
      assert.equal(ranges[1].status, 416);
      assert.equal(ranges[2].status, 416);
      await waitForSongIllustrations(page);
      await page.screenshot({ path: path.join(output, 'song-offline-desktop.png'), fullPage: true });
      await context.setOffline(false);
      assert.deepEqual(await page.evaluate(() => window.__mediaTest.webAudio), []);
      assert.deepEqual(pageErrors, []);
    }, true, true);

    await check('new songs, toggling, and stop-all cancel actual pending native play requests', async () => {
      const pendingContext = await browser.newContext({ serviceWorkers: 'block' });
      await pendingContext.addInitScript(instrument);
      const pendingPage = await pendingContext.newPage();
      const held = [];
      await pendingPage.route('**/audio/**', route => { held.push(route); });
      try {
        await pendingPage.goto(url);
        const pendingSongs = songs.slice(-2);
        const button = pendingPage.locator('[data-song="' + pendingSongs[0].id + '"]');
        await button.click();
        assert.equal(await pendingPage.locator('#native-players audio').count(), 1);
        assert.equal(await button.getAttribute('aria-pressed'), 'true');
        assert.equal(await button.getAttribute('aria-label'), 'Stoppa ' + pendingSongs[0].name);
        const player = await pendingPage.locator('#native-players audio').elementHandle();
        const replacement = pendingPage.locator('[data-song="' + pendingSongs[1].id + '"]');
        await replacement.click();
        assert.equal(await pendingPage.locator('#layer').isChecked(), true);
        assert.equal(await pendingPage.locator('#native-players audio').count(), 1);
        assert.deepEqual(await player.evaluate(audio => ({ connected: audio.isConnected, src: audio.getAttribute('src'), paused: audio.paused })), { connected: false, src: null, paused: true });
        assert.equal(await button.getAttribute('aria-pressed'), 'false');
        assert.equal(await replacement.getAttribute('aria-pressed'), 'true');
        assert.equal(await pendingPage.locator(songSelector + '[aria-pressed="true"]').count(), 1);
        await pendingPage.waitForFunction(() => window.__mediaTest.calls[0].result === 'AbortError');
        const replacementPlayer = await pendingPage.locator('#native-players audio').elementHandle();
        await replacement.click();
        assert.equal(await pendingPage.locator('#native-players audio').count(), 0);
        assert.deepEqual(await replacementPlayer.evaluate(audio => ({ connected: audio.isConnected, src: audio.getAttribute('src'), paused: audio.paused })), { connected: false, src: null, paused: true });
        assert.equal(await replacement.getAttribute('aria-pressed'), 'false');
        await pendingPage.waitForFunction(() => window.__mediaTest.calls[1].result === 'AbortError');
        await button.click();
        await pendingPage.locator('#stop').click();
        assert.equal(await pendingPage.locator('#native-players audio').count(), 0);
        assert.equal(await button.getAttribute('aria-pressed'), 'false');
        await pendingPage.waitForFunction(() => window.__mediaTest.calls.at(-1).result === 'AbortError');
        await pendingPage.unroute('**/audio/**');
        await Promise.allSettled(held.map(route => route.fulfill({ status: 200, contentType: mime[path.extname(route.request().url())], body: fs.readFileSync(path.join(root, new URL(route.request().url()).pathname.slice(1))) })));
        await pendingPage.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        assert.equal(await pendingPage.locator('#native-players audio').count(), 0);
        assert.deepEqual(await pendingPage.evaluate(() => window.__mediaTest.playing), []);
        assert.deepEqual(await pendingPage.evaluate(() => window.__mediaTest.webAudio), []);
      } finally { await pendingContext.close(); }
    });

    await check('all twelve song titles and artist captions fit desktop, tablet, and narrow mobile cards', async () => {
      const responsiveGeometry = [];
      try {
        for (const width of [320, 390, 768, 1024]) {
          await page.setViewportSize({ width, height: 844 });
          const layout = await page.locator(songSelector).evaluateAll(buttons => buttons.map(button => {
            const card = button.getBoundingClientRect();
            const icon = button.querySelector('.song-icon');
            const geometry = icon.getBBox();
            const matrix = icon.getScreenCTM();
            const corners = [[geometry.x, geometry.y], [geometry.x + geometry.width, geometry.y], [geometry.x, geometry.y + geometry.height], [geometry.x + geometry.width, geometry.y + geometry.height]].map(([x, y]) => new DOMPoint(x, y).matrixTransform(matrix));
            const painted = { left: Math.min(...corners.map(point => point.x)), right: Math.max(...corners.map(point => point.x)), top: Math.min(...corners.map(point => point.y)), bottom: Math.max(...corners.map(point => point.y)) };
            return { id: button.dataset.song, illustration: { painted, insideCard: painted.left >= card.left && painted.right <= card.right && painted.top >= card.top && painted.bottom <= card.bottom, insideViewport: painted.left >= 0 && painted.right <= innerWidth }, contents: ['.name', 'small', '.song-art'].map(selector => {
              const element = button.querySelector(selector);
              const box = element.getBoundingClientRect();
              // Decorative thought bubbles extend outside the art capsule; text must fit its own box.
              return { selector, inside: box.left >= card.left && box.right <= card.right && box.top >= card.top && box.bottom <= card.bottom, fits: selector === '.song-art' || element.scrollWidth <= element.clientWidth + 1 && element.scrollHeight <= element.clientHeight + 1 };
            }) };
          }));
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, width + 'px page has no horizontal overflow');
          for (const song of layout) {
            assert.equal(song.illustration.insideCard, true, width + 'px ' + song.id + ' painted SVG geometry stays inside its card');
            assert.equal(song.illustration.insideViewport, true, width + 'px ' + song.id + ' painted SVG geometry stays inside the viewport');
            for (const content of song.contents) {
              assert.equal(content.inside, true, width + 'px ' + song.id + ' ' + content.selector + ' stays inside its card');
              assert.equal(content.fits, true, width + 'px ' + song.id + ' ' + content.selector + ' is fully visible');
            }
          }
          const hero = await page.evaluate(() => {
            const mascot = document.querySelector('.hero-mascot').getBoundingClientRect();
            return ['.page-header h1', '.hero-tagline'].map(selector => {
              const box = document.querySelector(selector).getBoundingClientRect();
              return { selector, overlapsMascot: box.left < mascot.right && box.right > mascot.left && box.top < mascot.bottom && box.bottom > mascot.top };
            });
          });
          for (const item of hero) assert.equal(item.overlapsMascot, false, width + 'px hero mascot leaves ' + item.selector + ' clear');
          responsiveGeometry.push({ width, hero, songs: layout });
          if (width === 320 || width === 768) await page.screenshot({ path: path.join(output, width === 320 ? 'song-mobile-320.png' : 'song-tablet.png'), fullPage: true });
        }
      } finally {
        fs.writeFileSync(path.join(output, 'responsive-geometry.json'), JSON.stringify(responsiveGeometry, null, 2) + '\n');
        await page.setViewportSize({ width: 1024, height: 1000 });
      }
    }, true, true);

    const screenPath = path.join(output, 'song-desktop.png');
    await page.screenshot({ path: screenPath, fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, 'song-mobile.png'), fullPage: true });
    console.log('Screenshots: ' + screenPath + ', ' + path.join(output, 'song-mobile.png'));
  } finally {
    await context?.close();
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
  fs.writeFileSync(path.join(output, designOnly ? 'song-design-results.json' : replacementOnly ? 'song-replacement-results.json' : 'song-playback-results.json'), JSON.stringify({ mode: designOnly ? 'design-only' : replacementOnly ? 'replacement-only' : 'full', reports, failed: errors.length }, null, 2) + '\n');
  if (errors.length) throw new Error(errors.length + ' verification group(s) failed');
  console.log(designOnly ? 'Design, cache integrity, and offline illustration verification passed.' : replacementOnly ? 'Replacement native playback, full-cache integrity, and offline verification passed.' : 'All native playback and offline verification passed.');
}

main().catch(error => { console.error(error.stack); process.exitCode = 1; });
