# Release 4.5.2 - Bromance-refrängen

Bromance now plays the instrumental main-lead/drop (chorus) melody from
Bromance (Arena) through the same wet recorded fart instrument. The five song
buttons remain Greta Gris, Björnen sover, Baby Shark,
En livstid i krig and Bromance. The other four approved recordings are unchanged.

Version 4.5.2 refreshes the offline cache with the revised Bromance recording.
The app still contains fourteen native HTML audio recordings and twenty-nine
complete cached assets. Only one song plays at a time, including with
Fisorkester enabled; selecting it again stops it.

Arrangement references and audio measurements are in audio/songs/CREDITS.md
and metadata.json. Targeted validation commands:

```sh
node tests/service-worker.cjs --require-assets
node tests/song-playback.cjs --replacement-only
```

These checks cover the unchanged five-button order, real native Bromance
playback online and offline, exclusive song switching, complete cached payload
hashes, all five song byte ranges, and the four retained recording hashes.
The Bromance hash must also differ from the previous 4.5.1 piano intro recording.
