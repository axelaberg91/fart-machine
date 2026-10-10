# Release 4.4.2 - En sång i taget och Baby Shark

Six new song buttons play Blinka lilla stjärna, Bä bä vita lamm, Broder Jakob,
Imse vimse spindel, Björnen sover and Baby Shark using pitched samples of the
app's existing CC0 Blöta recording by Breviceps and Trumpeten recording by sorce.
Each note uses recorded wet fart sounds for its onset and texture, with a pitched
fart body carrying the melody. Each button plays a complete instrumental
arrangement with no singing or other instruments.

- Song playback uses prerecorded local MP3 files and the same native HTML audio
  player as the nine original pads. Playback starts directly from the user's tap.
- Starting a song stops the previous song, including a pending start, even with
  Fisorkester enabled. Tap an active song again to stop it. Stoppa allt, volume,
  Fisorkester, the audio test player and page hiding share the existing playback lifecycle.
- Song buttons show their playing state and expose play/stop labels to assistive
  technology. The song grid has three columns on larger screens and two on phones.
- Version 4.4.2 caches all six songs with the app, original recordings and photos.
  The previous offline version remains available if any new asset fails to cache.
- Song arrangements, source credits and the rendering tool are included in the
  repository so the bundled recordings can be reproduced.

Validation passed in Chrome on Windows: all fifteen actual MP3 recordings decode
and play from synchronous trusted button clicks, both online and after an offline
reload. Web Audio access was configured to throw and was never used. Song toggles,
pending-play cancellation, stop-all, overlapping/exclusive playback, volume,
accessibility labels and page hiding passed. All thirty offline assets were
verified byte for byte, including song byte-range, suffix-range and invalid-range
responses. JavaScript syntax checks and independent range tests passed.

The six arrangements are 16.8–21.1 seconds long and total about 1.38 MB. Offline
decoding verified mono MP3 audio at 44.1 kHz and 96 kbps, with no clipped samples.
Desktop and 390-pixel phone layouts were visually checked with no overflow.

Run `node tests/service-worker.cjs --require-assets` and
`node tests/song-playback.cjs` (the browser suite requires Playwright and Chrome,
Edge or an installed Playwright Chromium). Use `CHROME_PATH` for a custom browser
path and `SONG_TEST_OUTPUT` for screenshots and the verification report.

Device limit: no physical iPad or iPhone audition has been performed.
