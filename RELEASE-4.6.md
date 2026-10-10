# Release 4.6.0 - Sommar och sol

Sommar och sol by Markoolio joins the song board as a sixth button. Its short
chorus clip uses the same wet recorded fart instrument. The six songs are Greta
Gris, Björnen sover, Baby Shark, En livstid i krig, Bromance and Sommar och sol,
in that order. The five existing song recordings remain exactly unchanged.

Version 4.6.0 caches all fifteen native HTML audio recordings, photos and app
shell as thirty complete assets. Only one song plays at a time, including with
Fisorkester enabled. Tapping it again stops it. Volume, Stoppa allt and the
nine original pads retain their existing behavior.

Arrangement references, composition credits and audio measurements are in
audio/songs/CREDITS.md and metadata.json. Targeted validation commands:

```sh
node tests/service-worker.cjs --require-assets
node tests/song-playback.cjs --replacement-only
```

These checks cover the six-button order, native Sommar och sol playback online
and offline, exclusive song switching, complete cached payload hashes, all six
song byte ranges, and the five unchanged recording hashes.
