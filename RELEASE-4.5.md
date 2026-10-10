# Release 4.5.0 - Åtta låtar med fisar

The song board now contains Paw Patrol, Lover (Taylor Swift), The Puerto Rico Song
(the AI hit by Bill Stiteler / saxboybilly18), Greta Gris, Björnen sover, Baby Shark,
En livstid i krig (Sabaton) and Ghosts ’n’ Stuff (deadmau5).

The first four replace Blinka lilla stjärna, Bä bä vita lamm, Broder Jakob and
Imse vimse spindel. The final two are additional buttons. Björnen sover and
Baby Shark retain their approved audio bytes. All new clips use the same wet
recorded Blöta and pitched Trumpeten fart instrument. The original nine sound
pads are retained.

Only one song can play at a time, including when Fisorkester is enabled. A new
selection cancels both playing and pending songs. Tapping the current song again
stops it. Volume, Stoppa allt and page hiding keep their existing behavior.

The app plays bundled MP3 recordings through native HTML audio, synchronously
from the user's tap. It needs no Web Audio, runtime synthesis or external music
service. Version 4.5.0 caches all eight songs and the app's original recordings,
photos and shell. The cache installs completely before replacing the old version.

Arrangement notes, references, composer credits, source recording credits and
audio validation measurements are in audio/songs/CREDITS.md and metadata.json.
The CC0 licenses cover the two source fart recordings, separately from the
compositions being performed.

Validation commands:

```sh
node tests/service-worker.cjs --require-assets
node tests/song-playback.cjs
```

The browser suite checks real native playback, one-song switching, pending-play
cancellation, volume, original-pad layering, accessible button states and offline
playback. It compares cached bytes and hashes with the local assets and checks
normal, suffix and invalid MP3 byte ranges. A retained-audio check verifies that
Björnen sover and Baby Shark remain unchanged.

Device limit: no physical iPad or iPhone audition has been performed.
