'use strict';
(() => {
  const VERSION = '3.0';
  const sounds = [
    ['smygaren', '\u{1f4a8}', 'Smygaren'],
    ['kanonen', '\u{1f4a5}', 'Kanonen'],
    ['blota', '\u{1fae7}', 'Bl\u00f6ta'],
    ['trumpeten', '\u{1f3ba}', 'Trumpeten'],
    ['ankan', '\u{1f986}', 'Ankan'],
    ['vulkanen', '\u{1f30b}', 'Vulkanen'],
    ['snabbisen', '\u26a1', 'Snabbisen'],
    ['raketen', '\u{1f680}', 'Raketen'],
    ['katastrofen', '\u2622\ufe0f', 'Katastrofen']
  ].map(([id, emoji, name]) => ({id, emoji, name, url: './audio/' + id + '.mp3'}));
  const grid = document.getElementById('grid');
  const volume = document.getElementById('vol');
  const layer = document.getElementById('layer');
  const status = document.getElementById('status');
  const offline = document.getElementById('offline');
  const bytes = new Map(), buffers = new Map(), voices = new Set();
  let context, master, compressor, generation = 0, interacted = false;

  for (const sound of sounds) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'sound';
    button.dataset.sound = sound.id;
    button.setAttribute('aria-label', 'Spela ' + sound.name);
    const emoji = document.createElement('span');
    emoji.className = 'emoji';
    emoji.setAttribute('aria-hidden', 'true');
    emoji.textContent = sound.emoji;
    const name = document.createElement('span');
    name.textContent = sound.name;
    const badge = document.createElement('small');
    badge.textContent = 'Laddar ...';
    button.append(emoji, name, badge);
    sound.button = button;
    sound.badge = badge;
    button.addEventListener('click', () => { interacted = true; void play(sound); });
    grid.appendChild(button);
  }

  // Only fetch existing MP3 recordings. There is no oscillator or synthesized fallback.
  function loadBytes(sound) {
    if (!bytes.has(sound.id)) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 15000);
      const promise = fetch(sound.url, {signal: controller.signal})
        .then(response => {
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.arrayBuffer();
        })
        .then(data => {
          if (data.byteLength < 100) throw new Error('Empty recording');
          sound.badge.textContent = 'INSPELAD';
          return data;
        })
        .catch(error => {
          bytes.delete(sound.id);
          sound.badge.textContent = 'Tryck f\u00f6r att f\u00f6rs\u00f6ka igen';
          throw error;
        })
        .finally(() => clearTimeout(timer));
      bytes.set(sound.id, promise);
    }
    return bytes.get(sound.id);
  }

  // Must be called directly from the tap handler to unlock audio on iPhone/iPad.
  function unlockAudio() {
    if (!context) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) throw new Error('Web Audio not supported');
      context = new AudioContextClass();
      compressor = context.createDynamicsCompressor();
      compressor.threshold.value = -10;
      compressor.knee.value = 12;
      compressor.ratio.value = 12;
      compressor.attack.value = 0.003;
      compressor.release.value = 0.15;
      master = context.createGain();
      master.gain.value = Number(volume.value) / 100 * 0.8;
      compressor.connect(master);
      master.connect(context.destination);
    }
    return context.state === 'running' ? Promise.resolve() : context.resume();
  }

  volume.addEventListener('input', () => {
    if (master) master.gain.setTargetAtTime(Number(volume.value) / 100 * 0.8, context.currentTime, 0.02);
  });

  function stopAll() {
    generation++; // Also cancels taps still waiting for a fetch or decode.
    for (const voice of voices) {
      try { voice.source.stop(); } catch (_) { /* Already stopped. */ }
      voice.source.disconnect();
    }
    voices.clear();
    sounds.forEach(sound => sound.button.classList.remove('playing'));
    status.textContent = '\u{1f92b} Tyst!';
  }
  document.getElementById('stop').addEventListener('click', () => { interacted = true; stopAll(); });

  async function play(sound) {
    if (!layer.checked) stopAll();
    const ticket = generation;
    try {
      const unlocked = unlockAudio();
      status.textContent = sound.emoji + ' ' + sound.name + ' ...';
      const [data] = await Promise.all([loadBytes(sound), unlocked]);
      if (ticket !== generation) return;
      if (!buffers.has(sound.id)) {
        const decoded = context.decodeAudioData(data.slice(0)).catch(error => {
          buffers.delete(sound.id);
          throw error;
        });
        buffers.set(sound.id, decoded);
      }
      const buffer = await buffers.get(sound.id);
      if (ticket !== generation) return;
      // Bound simultaneous voices, while still allowing all nine buttons together.
      if (voices.size >= 12) {
        const oldest = voices.values().next().value;
        oldest.source.stop();
        oldest.source.disconnect();
        voices.delete(oldest);
      }
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(compressor);
      const voice = {source, sound};
      voices.add(voice);
      source.onended = () => {
        source.disconnect();
        voices.delete(voice);
        if (![...voices].some(v => v.sound === sound)) sound.button.classList.remove('playing');
      };
      source.start();
      sound.button.classList.add('playing');
      status.textContent = sound.emoji + ' ' + sound.name + '!';
    } catch (error) {
      if (ticket === generation) status.textContent = 'Kunde inte spela ' + sound.name + '. Kontrollera anslutningen och tryck igen.';
      console.warn('Recording playback failed:', sound.id, error);
    }
  }

  let loaded = 0;
  Promise.allSettled(sounds.map(sound => loadBytes(sound).then(() => {
    loaded++;
    if (!interacted) status.textContent = 'Laddar inspelningar ' + loaded + '/9 ...';
  }))).then(() => {
    if (!interacted) status.textContent = loaded === 9 ? '\u{1f446} V\u00e4lj din prutt! Nio inspelningar redo.' : 'Vissa ljud saknas. Anslut till internet och tryck igen.';
  });

  async function prepareOffline() {
    if (!('serviceWorker' in navigator) || !window.isSecureContext) {
      offline.textContent = 'Offlinel\u00e4ge kr\u00e4ver en webbl\u00e4sare med st\u00f6d och en HTTPS-adress.';
      return;
    }
    let hadController = Boolean(navigator.serviceWorker.controller);
    let reloading = false;
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
          offline.textContent = 'Redo offline \u2013 9/9 ljud sparade';
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
    } catch (error) {
      offline.textContent = 'Offlinel\u00e4get kunde inte starta. Ladda om med internetanslutning.';
      console.warn('Offline setup failed:', error);
    }
  }
  void prepareOffline();
})();
