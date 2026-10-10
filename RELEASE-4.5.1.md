# Release 4.5.1 - Fem låtar och Bromance

The song board now contains Greta Gris, Björnen sover, Baby Shark,
En livstid i krig (Sabaton) and Bromance by Avicii.
Lover, Paw Patrol and The Puerto Rico Song have been removed; Bromance
replaces Ghosts ’n’ Stuff.

The four retained songs keep their approved recordings. Bromance uses the same
wet recorded Blöta and pitched Trumpeten fart instrument. All fourteen recordings
play through native HTML audio from the user's tap. Only one song plays at a
time, including with Fisorkester enabled; tapping it again stops it. The nine
original sound pads, volume and Stoppa allt retain their existing behavior.

Version 4.5.1 caches the five songs, nine original recordings, photos and app
shell as twenty-nine complete assets. Arrangement references, composition credits
and audio validation are in audio/songs/CREDITS.md and metadata.json.

Validation commands:

```sh
node tests/service-worker.cjs --require-assets
node tests/song-playback.cjs --replacement-only
```

The targeted browser checks cover the five buttons and their accessible names,
real native Bromance playback online and offline, exclusive song switching,
complete cached payload hashes and all five song byte ranges. The retained-audio
check compares the four unchanged recordings against their approved hashes.
The full behavior suite remains available with node tests/song-playback.cjs.
