# Release 4.3 - Native recorded-audio playback

The iPad user reported that opening the MP3 separately works but the app does not. The precise device-specific root cause is not confirmed.

- Replaced the active Web Audio implementation with native HTMLAudioElement playback for every pad. No AudioContext, decodeAudioData, gain node, compressor, or AudioSession override is used by the new player.
- Calls audio.play() synchronously inside the user's click; it never waits for a download or decode before requesting playback.
- Preloads unchanged MP3 bytes as audio/mpeg Blob URLs so prepared clips play locally without going through HTTP media range requests. Direct native URL playback remains available when prefetch fails.
- A fresh player is created per tap; Stop all and page hiding cancel active and pending playback. Maximum 12 simultaneous players. Playback rejection is handled without automatic retry.
- On iPad/iPhone, replaces the software volume slider with a device-volume-buttons hint. Keeps desktop volume, orchestra, photos, title, audio files and licensing unchanged.
- Uses the new app-v4.3.js filename and Version 4.3 offline cache to avoid mixing older player code with the new page.

Validation actually performed: JavaScript syntax checks; all nine pad actions with MP3 fixtures in Chromium, checking native playback progress and synchronous trusted-click calls; Web Audio access deliberately throws in the test; blocked-play retry, Stop all, overlap mode, voice cap and pagehide cleanup; iPad-identification branch in Chromium. Service-worker installation, version rejection, 24-asset readiness, scoped cleanup and 206/416 byte ranges passed in-memory unit tests.

Limits: browser network access was restricted, so resources/MP3 fixtures were supplied in memory. No end-to-end hosted-site test, Safari test or physical iPad audition was performed. Original recordings and photos are unchanged, not replaced with test fixtures.

Primary reference for direct user-gesture playback: https://webkit.org/blog/6784/new-video-policies-for-ios/
