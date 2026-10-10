# Release 4.6.1 - Sommartider

Sommartider replaces Sommar och sol as the sixth song button. The clip uses
the recurring title/chorus hook, played through the same wet recorded fart
instrument. The other songs remain Greta Gris, Björnen sover, Baby Shark,
En livstid i krig and Bromance, with their approved recordings unchanged.

Version 4.6.1 caches all fifteen native HTML audio recordings, photos and app
shell as thirty complete assets. Songs still play one at a time, including with
Fisorkester enabled. Tapping the current song stops it. Volume, Stoppa allt and
the nine original pads retain their existing behavior.

Arrangement references, composition credits and audio measurements are in
audio/songs/CREDITS.md and metadata.json. Targeted validation commands:

```sh
node tests/service-worker.cjs --require-assets
node tests/song-playback.cjs --replacement-only
```

These checks cover the six-button order, native Sommartider playback online
and offline, exclusive song switching and toggling, complete cached payload
hashes, all six song byte ranges, the five retained recording hashes, and removal
of the previous Sommar och sol recording.
