# Hugo och Hermans pruttmaskin

## 3.0 - Recorded audio

- Replaced the synthetic sound generator with nine different recorded MP3 clips.
- Bundled all nine clips in audio/; playback makes no requests to external sound services.
- CC0 sources, authors, SHA-256 checksums and file metadata: audio/sources.json and audio/CREDITS.md. Credits are also visible in the app.
- Preserved the app title, colourful nine-pad layout, volume, orchestra mode and Stop all.
- Added a visible Version 3.0 footer and offline-readiness indicator. Offline readiness requires all app resources and all nine clips to be cached.
- Installation is atomic: missing files do not replace the previous working offline version.
- Stops cancel pending playback as well as currently playing clips; simultaneous playback is limited to 12 voices.

Validation: all nine downloaded files passed MPEG Layer III structural checks and have distinct SHA-256 hashes. UI layout and player controls passed Chromium tests using local MP3 fixtures. Service-worker lifecycle and offline cache behavior passed in-memory unit tests. No physical iPhone/iPad audition or end-to-end Safari test has been performed.
