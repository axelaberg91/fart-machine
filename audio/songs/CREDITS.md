# Fart-song recordings

Six complete, solo instrumental melody verses, rendered offline from a real
recorded fart. There are no voices, backing instruments or external audio
requests. The app plays these finished MP3 files using native HTML audio.

## Recorded instrument

- Source file: `../trumpeten.mp3` (unchanged).
- Recording: **fart,bum,trumpet,poop.wav** by **sorce**.
- Source: https://freesound.org/people/sorce/sounds/431621/
- Source recording license: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
- SHA-256: `cf58ca41e3b6fb183995a099bc88e084df3561110aefc40ee9f9040cbd815c63`.

The sampled section is approximately 1.626–1.738 seconds into that recording.
Its measured fundamental is 250.874 Hz. A phase-aligned loop sustains the
original recorded waveform; resampled playback sets each melody note's pitch.
Short attack and release envelopes prevent clicks and articulate repeated notes.
No oscillator or added instrument produces the melody.

## Melodies

These are new solo sampled-fart renditions of the underlying traditional or
public-domain melodies. No modern performance or accompaniment is sampled.
The notation links below were used to verify melody notes; their page layouts,
modern arrangements, harmonies and audio are not included.

| File | Melody | Duration |
| --- | --- | --- |
| `blinka-lilla-stjarna.mp3` | Blinka lilla stjärna / Ah! vous dirai-je, maman (traditional) | 21.07 s |
| `ba-ba-vita-lamm.mp3` | Bä bä vita lamm, Alice Tegnér, *Sjung med oss, mamma!*, no. 5 (1892) | 18.66 s |
| `broder-jakob.mp3` | Broder Jakob / Frère Jacques (traditional) | 16.75 s |
| `imse-vimse-spindel.mp3` | Imse vimse spindel / Itsy Bitsy Spider (traditional) | 19.40 s |
| `bjornen-sover.mp3` | Björnen sover / Gubben Noak (traditional) | 21.07 s |
| `london-bridge.mp3` | London Bridge Is Falling Down (traditional) | 16.20 s |

**Bä bä vita lamm uses Alice Tegnér's Swedish melody**, which is different from
Blinka lilla stjärna and the English Baa, Baa, Black Sheep melody.

Notation references:

- [Alice Tegnér's original score, pages 10–11](https://runeberg.org/sjungmamma/1/0010.html)
  ([page 11](https://runeberg.org/sjungmamma/1/0011.html)).
- [Bä bä vita lamm melody notation](https://www.spelapiano.org/noter/ba-ba-vita-lamm.html).
- [Blinka lilla stjärna and Björnen sover notation](https://ciss.se/munspel/barnvisor.html).
- [Broder Jakob opening notes](https://www.skolesaga.no/musikk-8/musikk-8-1-1).
- [Itsy Bitsy Spider melody notation](https://www.bethsnotesplus.com/wp-content/uploads/2024/11/Itsy-Bitsy-Spider.pdf).
- [London Bridge melody notation](https://www.8notes.com/scores/18427.asp).

## Format, validation and regeneration

All six files are mono MPEG Layer III (MP3), 44,100 Hz, 96 kbit/s, MIME
`audio/mpeg`. Their combined size is approximately 1.36 MB. Decoded peak levels
are below 0.78 full scale with zero clipped samples. Autocorrelation checks of
the rendered notes found a maximum pitch error below 8 cents. These measurements
check the audio files themselves and do not claim testing on a physical iPad.

`metadata.json` records every melody note and duration, tempo, transposition,
source checksum, output checksum and validation result. Regenerate the assets
with Python, NumPy and FFmpeg:

```sh
python tools/render-songs.py --ffmpeg /path/to/ffmpeg
```

Rendering is a development step only. The deployed app needs no Python,
FFmpeg, audio synthesis or Web Audio API.
