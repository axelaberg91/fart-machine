'use strict';
(() => {
  const VERSION = '4.2';
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
  const grid = document.getElementById('grid');
  const volume = document.getElementById('vol');
  const layer = document.getElementById('layer');
  const status = document.getElementById('status');
  const offline = document.getElementById('offline');
  const bytes = new Map(), buffers = new Map(), voices = new Set();
  let context, master, compressor, generation = 0, interacted = false;
  let needsAudioReset = false;

  for (const [index, sound] of sounds.entries()) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'sound';
    button.dataset.sound = sound.id;
    button.setAttribute('aria-label', 'Spela ' + sound.name);
    const image = document.createElement('img');
    image.className = 'photo';
    image.src = './photos/photo-' + sound.photo + '.webp';
    image.alt = ''; // The button's accessible name describes its action.
    image.width = 126;
    image.height = 126;
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
        if (!layer.checked) sounds.forEach(item => item.button.classList.remove('playing'));
        button.classList.add('playing');
        setTimeout(() => button.classList.remove('playing'), 750);
        status.textContent = sound.emoji + ' ' + sound.name + ' \u2013 f\u00f6rhandsvisning utan ljud';
      } else {
        void play(sound);
      }
    });
    grid.appendChild(button);
  }

  // Same recorded MP3 assets as v3. No synthesis and no external audio requests.
  function loadBytes(sound) {
    if (!bytes.has(sound.id)) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 15000);
      sound.button.setAttribute('aria-busy', 'true');
      const promise = fetch(sound.url, {signal: controller.signal})
        .then(response => {
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.arrayBuffer();
        })
        .then(data => {
          if (data.byteLength < 100) throw new Error('Empty recording');
          sound.badge.textContent = ''; // No repeated recording label on pads.
          return data;
        })
        .catch(error => {
          bytes.delete(sound.id);
          sound.badge.textContent = 'Tryck f\u00f6r att f\u00f6rs\u00f6ka igen';
          throw error;
        })
        .finally(() => {
          clearTimeout(timer);
          sound.button.removeAttribute('aria-busy');
        });
      bytes.set(sound.id, promise);
    }
    return bytes.get(sound.id);
  }

  // WebKit bug 237322: Web Audio defaults to ambient on iOS, unlike media playback.
  // Feature-detect the API. Never request microphone permission or override device volume.
  function usePlaybackSession() {
    try {
      if (navigator.audioSession && navigator.audioSession.type !== 'playback') {
        navigator.audioSession.type = 'playback';
      }
    } catch (_) { /* Older browsers keep their default audio route. */ }
  }

  function withTimeout(promise, ms, name) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        const error = new Error(name);
        error.name = name;
        reject(error);
      }, ms);
      Promise.resolve(promise).then(value => {
        clearTimeout(timer); resolve(value);
      }, error => {
        clearTimeout(timer); reject(error);
      });
    });
  }

  function audioDebug(error) {
    const element = document.getElementById('audio-debug');
    if (!element) return;
    element.textContent = 'Version ' + VERSION + ' | Audio: ' + (context ? context.state : 'ej startat') +
      (error ? ' | ' + (error.name || 'Error') : '');
  }

  // Synchronous creation + resume + silent warm-up inside the user's tap, before any await.
  function unlockAudio() {
    usePlaybackSession();
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
      context.addEventListener('statechange', () => audioDebug());
    }
    const current = context;
    if (current.state === 'running') return Promise.resolve();
    const resumed = current.resume();
    const warmup = current.createBufferSource();
    warmup.buffer = current.createBuffer(1, 1, current.sampleRate);
    warmup.connect(current.destination);
    warmup.onended = () => warmup.disconnect();
    warmup.start(0); // One silent sample, not an audible synthesized sound.
    return withTimeout(resumed, 3000, 'AudioStartTimeout').then(() => {
      if (current.state !== 'running') {
        const error = new Error('Audio did not enter running state');
        error.name = 'AudioStartError';
        throw error;
      }
    }).catch(error => {
      if (current === context) needsAudioReset = true;
      throw error;
    });
  }

  function resetAudio() {
    stopAll();
    const previous = context;
    context = master = compressor = undefined;
    buffers.clear();
    needsAudioReset = false;
    if (previous && previous.state !== 'closed') {
      try { Promise.resolve(previous.close()).catch(() => {}); } catch (_) {}
    }
    audioDebug();
  }

  // Callback support also covers older Safari versions of decodeAudioData.
  function decodeRecording(data, audioContext) {
    return withTimeout(new Promise((resolve, reject) => {
      const result = audioContext.decodeAudioData(data.slice(0), resolve, reject);
      if (result && typeof result.then === 'function') result.then(resolve, reject);
    }), 10000, 'AudioDecodeTimeout');
  }

  volume.addEventListener('input', () => {
    if (master) master.gain.setTargetAtTime(Number(volume.value) / 100 * 0.8, context.currentTime, 0.02);
  });

  function stopAll() {
    generation++;
    const testPlayer = document.getElementById('audio-test');
    if (testPlayer) testPlayer.pause();
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
    if (needsAudioReset || (context && (context.state === 'closed' || context.state === 'interrupted'))) resetAudio();
    if (!layer.checked) stopAll();
    const ticket = generation;
    try {
      const unlocked = unlockAudio();
      status.textContent = sound.emoji + ' ' + sound.name + ' ...';
      const [data] = await Promise.all([loadBytes(sound), unlocked]);
      if (ticket !== generation) return;
      if (!buffers.has(sound.id)) {
        const decoded = decodeRecording(data, context).catch(error => {
          buffers.delete(sound.id);
          throw error;
        });
        buffers.set(sound.id, decoded);
      }
      const buffer = await buffers.get(sound.id);
      if (ticket !== generation) return;
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
      audioDebug();
    } catch (error) {
      if (ticket === generation) {
        status.textContent = 'Ljudet startade inte. Tryck igen eller \u00f6ppna Inget ljud? nedan.';
        audioDebug(error);
      }
      console.warn('Recording playback failed:', sound.id, error);
    }
  }

  if (preview) {
    document.body.classList.add('is-preview');
    status.textContent = 'V\u00e4lj din prutt!';
    offline.textContent = 'F\u00f6rhandsvisning av temat \u00b7 ljuden \u00e4r inte aktiva';
    return;
  }

  const resetButton = document.getElementById('reset-audio');
  if (resetButton) resetButton.addEventListener('click', () => {
    interacted = true;
    resetAudio();
    void play(sounds[6]);
  });
  const testPlayer = document.getElementById('audio-test');
  if (testPlayer) testPlayer.addEventListener('play', usePlaybackSession);
  // Do not leave queued sounds waiting to play after the screen unlocks.
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      stopAll();
      needsAudioReset = Boolean(context);
    }
  });
  window.addEventListener('pagehide', () => {
    stopAll();
    needsAudioReset = Boolean(context);
  });
  audioDebug();

  let loaded = 0;
  Promise.allSettled(sounds.map(sound => loadBytes(sound).then(() => {
    loaded++;
    if (!interacted) status.textContent = 'Laddar ljud ' + loaded + '/9 ...';
  }))).then(() => {
    if (!interacted) status.textContent = loaded === 9 ? '\u{1f446} V\u00e4lj din prutt!' : 'Vissa ljud saknas. Anslut till internet och tryck igen.';
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
          offline.textContent = 'Redo offline \u2013 ljud och bilder sparade';
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
