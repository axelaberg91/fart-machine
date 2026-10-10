'use strict';
(() => {
  const VERSION = '4.6.0';
  const preview = document.body.dataset.preview === 'true' || new URL(location.href).searchParams.get('preview') === '1';
  const sounds = [
    ['smygaren', '\u{1f4a8}', 'Smygaren', '01'],
    ['kanonen', '\u{1f4a5}', 'Kanonen', '04'],
    ['blota', '\u{1fae7}', 'Bl\u00f6ta', '06'],
    ['trumpeten', '\u{1f3ba}', 'Trumpeten', '07'],
    ['ankan', '\u{1f986}', 'Ankan', '09'],
    ['vulkanen', '\u{1f30b}', 'Vulkanen', '03'],
    ['snabbisen', '\u26a1', 'Snabbisen', '02'],
    ['raketen', '\u{1f680}', 'Raketen', '05'],
    ['katastrofen', '\u2622\ufe0f', 'Katastrofen', '08']
  ].map(([id, emoji, name, photo]) => ({id, emoji, name, photo, url: './audio/' + id + '.mp3'}));
  const songs = [
    ['greta-gris', '\u{1f437}', 'Greta Gris'],
    ['bjornen-sover', '\u{1f43b}', 'Bj\u00f6rnen sover'],
    ['baby-shark', '\u{1f988}', 'Baby Shark'],
    ['en-livstid-i-krig', '\u2694\ufe0f', 'En livstid i krig'],
    ['bromance', '\u{1f3a7}', 'Bromance'],
    ['sommar-och-sol', '\u{1f31e}', 'Sommar och sol']
  ].map(([id, emoji, name]) => ({id, emoji, name, song: true, url: './audio/songs/' + id + '.mp3'}));
  const recordings = [...sounds, ...songs];
  const grid = document.getElementById('grid');
  const songGrid = document.getElementById('songs');
  const volume = document.getElementById('vol');
  const layer = document.getElementById('layer');
  const status = document.getElementById('status');
  const offline = document.getElementById('offline');
  const testPlayer = document.getElementById('audio-test');
  const voices = new Set();
  const mediaHost = document.createElement('div');
  mediaHost.hidden = true;
  mediaHost.id = 'native-players';
  document.body.appendChild(mediaHost);
  let interacted = false;

  // Native iOS media volume is controlled by the device, not a Web Audio gain node.
  const hardwareVolume = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  if (hardwareVolume) {
    volume.hidden = true;
    volume.disabled = true;
    const hint = document.createElement('span');
    hint.textContent = 'Anv\u00e4nd enhetens volymknappar';
    hint.style.fontSize = '11px';
    volume.insertAdjacentElement('afterend', hint);
  }

  function debug(state, error) {
    const element = document.getElementById('audio-debug');
    if (element) element.textContent = 'Version ' + VERSION + ' | Spelare: HTML audio | ' + state +
      (error ? ' | ' + (error.name || 'MediaError') + (error.code ? ' ' + error.code : '') : '');
  }

  for (const [index, sound] of sounds.entries()) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'sound';
    button.dataset.sound = sound.id;
    button.setAttribute('aria-label', 'Spela ' + sound.name);
    const image = document.createElement('img');
    image.className = 'photo';
    image.src = './photos/photo-' + sound.photo + '.webp';
    image.alt = '';
    image.width = image.height = 126;
    image.draggable = false;
    const emoji = document.createElement('span');
    emoji.className = 'emoji';
    emoji.setAttribute('aria-hidden', 'true');
    emoji.textContent = sound.emoji;
    const number = document.createElement('span');
    number.className = 'number';
    number.setAttribute('aria-hidden', 'true');
    number.textContent = String(index + 1).padStart(2, '0');
    const name = document.createElement('span');
    name.className = 'name';
    name.textContent = sound.name;
    const badge = document.createElement('small');
    const burst = document.createElement('span');
    burst.className = 'burst';
    burst.setAttribute('aria-hidden', 'true');
    burst.textContent = 'PRRRT!';
    button.append(number, emoji, image, name, badge, burst);
    sound.button = button;
    sound.badge = badge;
    button.addEventListener('click', () => {
      interacted = true;
      if (preview) {
        button.classList.add('playing');
        setTimeout(() => button.classList.remove('playing'), 750);
        status.textContent = sound.name + ' \u2013 f\u00f6rhandsvisning utan ljud';
      } else {
        play(sound); // Synchronous: no fetch, decoding, timer or await before audio.play().
      }
    });
    grid.appendChild(button);
  }

  for (const [index, song] of songs.entries()) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'sound song';
    button.dataset.sound = button.dataset.song = song.id;
    button.setAttribute('aria-pressed', 'false');
    button.setAttribute('aria-label', 'Spela ' + song.name);
    const number = document.createElement('span');
    number.className = 'number';
    number.setAttribute('aria-hidden', 'true');
    number.textContent = String(index + 1).padStart(2, '0');
    const art = document.createElement('span');
    art.className = 'song-art';
    art.setAttribute('aria-hidden', 'true');
    const emoji = document.createElement('span');
    emoji.className = 'emoji';
    emoji.textContent = song.emoji;
    art.appendChild(emoji);
    const name = document.createElement('span');
    name.className = 'name';
    name.textContent = song.name;
    const badge = document.createElement('small');
    badge.textContent = 'Fisar i takt';
    const burst = document.createElement('span');
    burst.className = 'burst';
    burst.setAttribute('aria-hidden', 'true');
    burst.textContent = 'STOPPA \u25a0';
    button.append(number, art, name, badge, burst);
    song.button = button;
    song.badge = badge;
    button.addEventListener('click', () => {
      interacted = true;
      const active = [...voices].filter(voice => voice.sound === song);
      if (active.length || song.previewTimer) {
        active.forEach(finish);
        clearTimeout(song.previewTimer);
        song.previewTimer = null;
        updateButton(song);
        status.textContent = song.name + ' \u2013 stoppad';
        debug('Stoppad ' + song.name);
      } else if (preview) {
        if (!layer.checked) stopAll();
        else stopSongs();
        song.previewTimer = setTimeout(() => {
          song.previewTimer = null;
          updateButton(song);
        }, 750);
        updateButton(song);
        status.textContent = song.name + ' \u2013 f\u00f6rhandsvisning utan ljud';
      } else {
        play(song); // Native playback starts synchronously in this trusted click.
      }
    });
    songGrid.appendChild(button);
  }

  function updateButton(sound) {
    const active = [...voices].filter(voice => voice.sound === sound);
    const isActive = Boolean(active.length || sound.previewTimer);
    sound.button.classList.toggle('playing', sound.song ? isActive : active.some(voice => voice.started));
    if (active.some(voice => !voice.started)) sound.button.setAttribute('aria-busy', 'true');
    else sound.button.removeAttribute('aria-busy');
    if (sound.song) {
      sound.button.setAttribute('aria-pressed', String(isActive));
      sound.button.setAttribute('aria-label', (isActive ? 'Stoppa ' : 'Spela ') + sound.name);
      sound.badge.textContent = isActive ? 'Tryck f\u00f6r att stoppa' : 'Fisar i takt';
    }
  }

  // Preload complete, unchanged recordings as Blobs. A Blob's native playback does not
  // use Safari's HTTP range/cache path. This happens ahead of taps, never blocks play().
  function prepareRecording(sound) {
    if (sound.loading) return sound.loading;
    if (sound.blobURL) return Promise.resolve(true);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    sound.loading = fetch(sound.url, {signal: controller.signal})
      .then(response => {
        if (!response.ok || response.status === 206) throw new Error('Incomplete recording');
        return response.arrayBuffer();
      })
      .then(data => {
        if (data.byteLength < 100) throw new Error('Empty recording');
        sound.blobURL = URL.createObjectURL(new Blob([data], {type: 'audio/mpeg'}));
        return true;
      })
      .catch(() => false) // Direct native playback is still available if prefetch fails.
      .finally(() => { clearTimeout(timer); sound.loading = null; });
    return sound.loading;
  }

  function finish(voice) {
    if (!voices.delete(voice)) return;
    clearTimeout(voice.timer);
    voice.audio.onplaying = voice.audio.onended = voice.audio.onerror = voice.audio.onpause = null;
    voice.audio.pause(); // Also cancels a pending play request; no delayed surprise sounds.
    voice.audio.removeAttribute('src');
    try { voice.audio.load(); } catch (_) {}
    voice.audio.remove();
    updateButton(voice.sound);
  }

  function stopSongs() {
    [...voices].filter(voice => voice.sound.song).forEach(finish);
    songs.forEach(song => {
      clearTimeout(song.previewTimer);
      song.previewTimer = null;
      updateButton(song);
    });
  }

  function stopAll() {
    [...voices].forEach(finish);
    if (testPlayer) testPlayer.pause();
    recordings.forEach(sound => {
      clearTimeout(sound.previewTimer);
      sound.previewTimer = null;
      updateButton(sound);
    });
    status.textContent = '\u{1f92b} Tyst!';
    debug('Stoppad');
  }

  function fail(voice, error) {
    if (!voices.has(voice)) return;
    // Retry with the original URL on the next deliberate tap if a Blob was rejected.
    if (voice.usedBlob && error && error.name !== 'NotAllowedError') voice.sound.direct = true;
    finish(voice);
    status.textContent = 'Ljudet startade inte. Tryck igen eller \u00f6ppna Inget ljud? nedan.';
    debug('Kunde inte starta ' + voice.sound.name, error);
  }

  function play(sound) {
    if (!layer.checked) stopAll();
    else {
      if (sound.song) stopSongs();
      if (testPlayer) testPlayer.pause();
    }
    while (voices.size >= 12) finish(voices.values().next().value);
    // A fresh native player avoids stale/paused audio contexts after iPad screen lock.
    // Never connect this element to Web Audio: that would reintroduce the failing path.
    const audio = document.createElement('audio');
    audio.preload = 'auto';
    audio.setAttribute('playsinline', '');
    audio.setAttribute('webkit-playsinline', '');
    if (!hardwareVolume) audio.volume = Number(volume.value) / 100 * 0.8;
    const usedBlob = Boolean(sound.blobURL && !sound.direct);
    audio.src = usedBlob ? sound.blobURL : sound.url;
    const voice = {audio, sound, usedBlob, started: false, timer: null};
    voices.add(voice);
    mediaHost.appendChild(audio);
    updateButton(sound);
    status.textContent = sound.emoji + ' ' + sound.name + ' ...';
    audio.onplaying = () => {
      if (!voices.has(voice)) return;
      clearTimeout(voice.timer);
      voice.started = true;
      updateButton(sound);
      status.textContent = sound.emoji + ' ' + sound.name + '!';
      debug('Spelar ' + sound.name + (usedBlob ? ' | Lokal ljudfil' : ' | Direkt ljudfil'));
    };
    audio.onended = () => finish(voice);
    audio.onpause = () => finish(voice);
    audio.onerror = () => fail(voice, audio.error);
    voice.timer = setTimeout(() => fail(voice, {name: 'StartTimeout'}), 12000);
    try {
      const result = audio.play(); // Must stay in this click event's synchronous call stack.
      if (result && typeof result.catch === 'function') result.catch(error => fail(voice, error));
    } catch (error) { fail(voice, error); }
    // A failed prefetch may succeed later, but never starts playback by itself.
    if (!sound.blobURL) void prepareRecording(sound);
  }

  document.getElementById('stop').addEventListener('click', () => { interacted = true; stopAll(); });
  layer.addEventListener('change', () => { if (!layer.checked) stopAll(); });
  volume.addEventListener('input', () => {
    if (!hardwareVolume) for (const voice of voices) voice.audio.volume = Number(volume.value) / 100 * 0.8;
  });

  if (preview) {
    document.body.classList.add('is-preview');
    status.textContent = 'V\u00e4lj din prutt!';
    offline.textContent = 'F\u00f6rhandsvisning utan ljud';
    return;
  }

  const resetButton = document.getElementById('reset-audio');
  if (resetButton) resetButton.addEventListener('click', () => {
    interacted = true;
    stopAll();
    play(sounds[6]);
  });
  if (testPlayer) testPlayer.addEventListener('play', () => {
    [...voices].forEach(finish);
    debug('Inbyggd testspelare');
  });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') stopAll();
  });
  window.addEventListener('pagehide', stopAll);
  debug('Redo');
  status.textContent = '\u{1f446} V\u00e4lj din prutt!';
  recordings.forEach(sound => { void prepareRecording(sound); });

  async function prepareOffline() {
    if (!('serviceWorker' in navigator) || !window.isSecureContext) {
      offline.textContent = 'Offlinel\u00e4ge kr\u00e4ver HTTPS och webbl\u00e4sarst\u00f6d.';
      return;
    }
    let hadController = Boolean(navigator.serviceWorker.controller), reloading = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (hadController && !reloading) {
        reloading = true;
        window.location.reload();
      }
      hadController = true;
    });
    function check(worker) {
      if (!worker) return;
      const channel = new MessageChannel();
      const timer = setTimeout(() => channel.port1.close(), 5000);
      channel.port1.onmessage = event => {
        clearTimeout(timer);
        channel.port1.close();
        if (event.data.version === VERSION && event.data.ready) {
          offline.textContent = 'Redo offline \u2013 ljud, ' + songs.length + ' l\u00e5tar och bilder sparade';
          offline.classList.add('ready');
        }
      };
      worker.postMessage({type: 'CACHE_STATUS'}, [channel.port2]);
    }
    try {
      const registration = await navigator.serviceWorker.register('./sw.js', {updateViaCache: 'none'});
      const observe = () => {
        const worker = registration.installing;
        if (!worker) return;
        worker.addEventListener('statechange', () => {
          if (worker.state === 'activated') check(registration.active);
          if (worker.state === 'redundant' && !offline.classList.contains('ready')) offline.textContent = 'Kunde inte spara allt offline. Ladda om med internetanslutning.';
        });
      };
      registration.addEventListener('updatefound', observe);
      observe();
      check(registration.active);
      navigator.serviceWorker.ready.then(ready => check(ready.active));
      registration.update().catch(() => {});
    } catch (_) {
      offline.textContent = 'Offlinel\u00e4get kunde inte starta. Ladda om med internetanslutning.';
    }
  }
  void prepareOffline();
})();
