# Release 4.7.0 - Through the Fire and Flames

Through the Fire and Flames by DragonForce joins the board as a seventh song.
The complete clip lasts ten seconds: its short guitar hook starts faithfully,
then deliberately stutters, falls out of tune, pauses and collapses into wet fart
sounds, as if the player has given up. The card says "Ett tappert
försök". The six existing songs and their approved recordings remain unchanged.

Version 4.7.0 caches all sixteen native HTML audio recordings, photos and app
shell as thirty-one complete assets. Only one song plays at a time, including
with Fisorkester enabled. Tapping the current song stops it. The nine original
pads, volume and Stoppa allt retain their existing behavior.

Arrangement references, composition credits and the intended musical and comic
sections are documented in audio/songs/CREDITS.md and metadata.json. Targeted
validation commands:

```sh
node tests/service-worker.cjs --require-assets
node tests/song-playback.cjs --replacement-only
```

These checks cover the seven-button order, native playback of the new song
online and offline with a ten-second duration check, exclusive song switching and toggling, complete cached
payload hashes, all seven song byte ranges and the six retained recording hashes.
