# Release 4.2 - iPad audio compatibility

- Feature-detect Audio Session and request playback on the user's tap. This addresses the iOS ambient/silent-mode behavior documented in WebKit bug 237322.
- Resume and warm the audio context synchronously inside the tap. A one-sample silent buffer is used only for initialization; the nine sound effects remain unchanged MP3 recordings.
- Bound pending audio-start and decode operations; rebuild the audio context on the next tap after a failed start or background interruption. No automatic playback after backgrounding.
- Support callback-style decodeAudioData as well as its Promise interface.
- Add a collapsed "Inget ljud?" section with a reset-and-test button, native audio control, direct recording link, and local diagnostic state.
- Support cached HTTP byte ranges for the native audio control. Keep atomic version-checked offline installation.
- Preserve all existing sound assets, photos, photo assignments, layout, and title. Bump the visible and cache versions to 4.2.

Validation performed: JavaScript syntax checks; Chromium with DOM/resources and MP3 test fixtures supplied in memory (controls, playback session, timeout/retry, callback decoding, unsupported AudioSession); in-memory service-worker tests for atomic failure, installation, version checks, cache cleanup, offline navigation and byte ranges. No physical iPad/Safari test has been performed. The user's particular root cause is not yet confirmed.

Primary reference: https://bugs.webkit.org/show_bug.cgi?id=237322#c6
