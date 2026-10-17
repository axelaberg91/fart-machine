#!/usr/bin/env python3
"""Render the eight solo fart-song MP3 assets offline. Requires Python, NumPy and FFmpeg.

Run: python tools/render-songs.py --ffmpeg /path/to/ffmpeg
The website plays the finished files through native HTML audio; this tool is
never loaded by the app. All instrument audio comes from the unchanged CC0
recordings audio/trumpeten.mp3, audio/blota.mp3 and audio/snabbisen.mp3.
The larger arrangements are rendered by render-orchestra.py and their metadata
is preserved when this tool regenerates the solo songs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RATE = 44100
SOURCE_SHA256 = "cf58ca41e3b6fb183995a099bc88e084df3561110aefc40ee9f9040cbd815c63"
WET_SHA256 = "a8709692b0719509700a38897f2de217b02f12af5f9a9a4768351623b8f8e8f2"
SHORT_SHA256 = "912a288d0e14f0d2e68e6904bb1215f9e38080e76d6adede7e0b488e24e8fb00"



def score(text):
    """Space-separated note:beat tokens; R is a rest."""
    return [(token.split(":")[0], float(token.split(":")[1])) for token in text.split()]


BROMANCE_CHORUS = (
    'G#5:0.75 G#5:0.75 G#5:0.75 B5:0.75 F#5:0.75 '
    'D#5:0.75 D#5:0.75 D#5:0.75 D#5:0.75 D#5:0.75 '
    'G#4:0.5 B4:0.5 E5:0.5 D#5:0.5 '
    'C#5:0.75 C#5:0.75 C#5:0.75 C#5:0.75 C#5:0.75 C#5:0.75 '
    'C#5:0.5 D#5:0.5 E5:0.5 F#5:0.5'
)

SOMMARTIDER_HOOK = (
    'C#4:0.5 E4:0.5 E4:0.5 C#4:0.5 F#4:1 F#4:1 '
    'F#4:0.5 F#4:0.5 F#4:0.5 E4:1.5 R:1'
)

PEPPA_HOOK = (
    'G4:1 E4:0.5 C4:0.5 D4:1 G3:1 G3:0.5 B3:0.5 D4:0.5 '
    'F4:0.5 E4:1 C4:1'
)

BEAR_VERSE = (
    'C4:1 C4:1 C4:1 E4:1 D4:1 D4:1 D4:1 F4:1 '
    'E4:1 E4:1 D4:1 D4:1 C4:4 E4:1 E4:1 E4:1 '
    'E4:1 G4:2 F4:2 D4:1 D4:1 D4:1 D4:1 F4:2 '
    'E4:2 C4:1 C4:1 C4:1 E4:1 D4:1 D4:1 D4:1 '
    'F4:1 E4:1 E4:1 D4:1 D4:1 C4:4'
)

BABY_SHARK_VERSE = (
    'D4:1 E4:1 G4:0.5 G4:0.5 G4:0.5 G4:0.25 G4:0.5 G4:0.25 '
    'G4:0.5 D4:0.5 E4:0.5 G4:0.5 G4:0.5 G4:0.5 G4:0.25 G4:0.5 '
    'G4:0.25 G4:0.5 D4:0.5 E4:0.5 G4:0.5 G4:0.5 G4:0.5 G4:0.25 '
    'G4:0.5 G4:0.25 G4:0.5 G4:0.5 G4:0.5 F#4:2'
)

SABATON_HOOK = (
    'G4:0.75 Bb4:0.75 D5:0.5 C5:1.5 C5:0.25 D5:0.25 Eb5:0.75 D5:0.75 '
    'Bb4:0.5 C5:2 Eb5:0.75 D5:0.75 Bb4:0.25 C5:0.25 Bb4:2 Bb4:0.75 '
    'Ab4:0.75 G4:0.5 F4:2 F4:0.75 G4:0.75 Ab4:0.5 G4:0.125 Ab4:0.125 '
    'G4:0.125 F4:0.125 G4:1.5'
)

# Compact solo hooks. Durations are quarter-note beats at the stated tempo.
SANDSTORM_HOOK = (
    'B4:0.25 B4:0.25 B4:0.25 B4:0.25 B4:0.5 '
    'B4:0.25 B4:0.25 B4:0.25 B4:0.25 B4:0.25 B4:0.25 B4:0.5 '
    'E5:0.25 E5:0.25 E5:0.25 E5:0.25 E5:0.25 E5:0.25 E5:0.5 '
    'D5:0.25 D5:0.25 D5:0.25 D5:0.25 D5:0.25 D5:0.25 D5:0.5 '
    'A4:0.25 A4:0.25 '
    'B4:0.25 B4:0.25 B4:0.25 B4:0.25 B4:0.5 '
    'B4:0.25 B4:0.25 B4:0.25 B4:0.25 B4:0.25 B4:0.25 B4:0.5 '
    'E5:0.25 E5:0.25 '
    'B4:0.25 B4:0.25 B4:0.25 B4:0.25 B4:0.5 '
    'B4:0.25 B4:0.25 B4:0.25 B4:0.25 B4:0.25 B4:0.25 B4:0.5 '
    'E5:0.25 E5:0.25'
)

RING_OF_FIRE_HOOK = (
    'D5:1 D5:0.5 D5:1 D5:0.5 D5:1 E5:1 C5:1 D5:4 '
    'B4:1 B4:0.5 B4:1 B4:0.5 B4:1 C5:1 A4:1 B4:4'
)

SONGS = [
    {'id': 'greta-gris',
     'title': 'Greta Gris',
     'bpm': 144,
     'transpose': -5,
     'meter': '4/4',
     'melody': 'Peppa Pig Main Theme — Julian Nott (2004)',
     'composition_rights': 'Copyrighted composition; CC0 applies only to the source fart recordings',
     'arrangement': 'Two-bar main-theme hook, repeated six times',
     'references': ['https://www.musicnotes.com/sheetmusic/piano-notion/peppa-pig-theme-song/MN0239242',
                    'https://conradschords.com/wp-content/uploads/2014/05/peppa-pig-theme-tune.pdf'],
     'notes': score(PEPPA_HOOK)*6},
    {'id': 'bjornen-sover',
     'title': 'Björnen sover',
     'bpm': 138,
     'transpose': -5,
     'meter': '4/4',
     'melody': 'Traditional: Gubben Noak / Björnen sover',
     'notes': score(BEAR_VERSE),
     'references': ['https://ciss.se/munspel/barnvisor.html']},
    {'id': 'baby-shark',
     'title': 'Baby Shark',
     'bpm': 112,
     'transpose': -12,
     'meter': '4/4',
     'melody': "Children's melody: Baby Shark (traditional chant, popularized by Pinkfong)",
     'notes': score(BABY_SHARK_VERSE)*2,
     'references': ['https://www.musicnotes.com/sheetmusic/childrens-song/baby-shark/MN0189377',
                    'https://www.stantons.com/scores/03746512.pdf',
                    'https://pianoletternotes.blogspot.com/2019/03/baby-shark-by-pinkfong.html']},
    {'id': 'en-livstid-i-krig',
     'title': 'En livstid i krig',
     'bpm': 68,
     'transpose': -12,
     'meter': '4/4, half-time notation',
     'melody': 'En livstid i krig — Joakim Brodén / Sabaton (2012)',
     'composition_rights': 'Copyrighted composition; CC0 applies only to the source fart recordings',
     'notes': score(SABATON_HOOK),
     'arrangement': 'Short opening lead melody; exact GP5 note durations and tied notes, with slide/hammer '
                    'targets represented as notes',
     'source_notation': 'Freely published Solo Guitar GP5 arrangement, opening measures 2 through the '
                        'first half of 7; written F4–Eb5 rendered F3–Eb4',
     'references': ['https://www.sabaton.net/discography/carolus-rex/en-livstid-i-krig/',
                    'https://gtptabs.com/tabs/19/sabaton/en-livstid-i-krig.html',
                    'https://gtptabs.com/tabs/download/55609.html',
                    'https://www.guitartabs.cc/tabs/s/sabaton/en_livstid_i_krig_tab.html']},
    {'id': 'bromance',
     'title': 'Bromance',
     'bpm': 126,
     'transpose': -24,
     'meter': '4/4',
     'melody': 'Bromance — Tim Berg / Tim Bergling (Avicii, 2010)',
     'composition_rights': 'Copyrighted composition; CC0 applies only to the source fart recordings',
     'arrangement': 'Instrumental main drop / chorus lead: four-bar melody repeated three times '
                    'at 126 BPM, starting directly on the main hook',
     'source_notation': 'Freely published Avicii Melodies MIDI by No_Literature4584, who credits '
                        'Keiric and TyphoonMusic; highest lead at beats 224–240, confirmed by '
                        'the identical repetition at 240–256. MIDI G#4–B5 rendered G#2–B3 '
                        'through one fixed transposition, preserving the register contour',
     'reference_validation': 'Pitch classes and syncopated onsets checked against the official '
                             'Arena preview from approximately 0.55 seconds; its mixed and '
                             'doubled instruments make octave identification less certain. '
                             'The solo follows the published MIDI lead with no per-note '
                             'octave changes',
     'references': ['https://sirupmusic.com/releases/bromance-aviciis-arena-mix/',
                    'https://www.qobuz.com/us-en/album/bromance-remixes-pt-2-tim-berg/7640130863125',
                    'https://music.apple.com/us/album/bromance-aviciis-arena-mix/1670446170?i=1670446174',
                    'https://www.reddit.com/r/avicii/comments/1jagvzf/52_avicii_melodies/',
                    'https://www.mediafire.com/file/d574ksdtv6qgw33/Avicii_Melodies.zip/file'],
     'notes': score(BROMANCE_CHORUS)*3},
    {'id': 'sommartider',
     'title': 'Sommartider',
     'bpm': 130,
     'transpose': -12,
     'meter': '4/4',
     'melody': 'Sommartider — Gyllene Tider; Per Gessle (1982)',
     'composition_rights': 'Copyrighted composition; CC0 applies only to the source fart recordings',
     'arrangement': 'Title / hej-hej refrain motif, repeated six times; four eighth-note '
                    'pickup notes followed by the repeated F-sharps and tied E, with one '
                    'quarter-note breathing rest completing each eight-beat loop',
     'source_notation': 'TheddyKeys published piano-arrangement preview, first system: the '
                        'melody pickup in bar 1, all of bar 2 and the first tied note of bar 3. '
                        'The E4 tie is merged into 1.5 beats. C#4–F#4 rendered C#3–F#3; '
                        '130 BPM is the published arrangement tempo',
     'reference_validation': 'Two independent visual readings agree on all ten melody notes '
                             'and durations. Fundamental and harmonic material in the official '
                             'original-release Apple preview supports the F-sharp to E contour; '
                             'the solo preserves the published melody register with a fixed '
                             'one-octave transposition',
     'references': ['https://mymusic5.com/Theddykeys/151169',
                    'https://music.apple.com/us/song/691335578',
                    'https://www.gyllenetider.com/discography/singles/sommartider/',
                    'https://www.gyllenetider.com/lyrics/',
                    'https://www.youtube.com/watch?v=4kVRF0hTeyQ'],
     'notes': score(SOMMARTIDER_HOOK)*6},
    {'id': 'sandstorm',
     'title': 'Sandstorm',
     'bpm': 140,
     'transpose': -12,
     'meter': '4/4',
     'melody': 'Sandstorm — Darude; Ville Virtanen / Jaakko Salovaara (1999)',
     'composition_rights': 'Copyrighted composition; CC0 applies only to the source fart recordings',
     'arrangement': 'Four-bar main synth riff, repeated three times at 140 BPM; alternating short Blota/Snabbisen attacks and a clear pitched fart body',
     'source_notation': 'Upper lead line of publicly shared MIDI, track 6, beats 72–88; all 56 note onsets preserved on the sixteenth-note grid. B4–E5–D5–A4 rendered one octave down',
     'articulation': 'tight-alternating',
     'alternate_attack': {'file': 'audio/snabbisen.mp3', 'sha256': SHORT_SHA256,
                          'author': 'C-V', 'license': 'CC0-1.0',
                          'source_page': 'https://freesound.org/people/C-V/sounds/506994/'},
     'references': ['https://www.musicnotes.com/sheetmusic/darude/sandstorm/MN0144488',
                    'https://bitmidi.com/darude_-_sandstorm-mid',
                    'https://www.cprato.com/en/midi/details/223/darude-sandstorm'],
     'notes': score(SANDSTORM_HOOK)*3},
    {'id': 'ring-of-fire',
     'title': 'Ring of Fire',
     'bpm': 114,
     'transpose': -12,
     'meter': '4/4 with 2/4 turnaround',
     'melody': 'Ring of Fire — Johnny Cash; June Carter / Merle Kilgore (1963)',
     'composition_rights': 'Copyrighted composition; CC0 applies only to the source fart recordings',
     'arrangement': 'Two-part trumpet hook, repeated twice; tied eighth notes merged and long notes shortened to four beats between phrases',
     'source_notation': 'Upper trumpet line in Gary Badger transcription; written F#5–G#5–E5–F#5 and D#5–E5–C#5–D#5 moved to D4–E4–C4–D4 and B3–C4–A3–B3 for the solo fart instrument',
     'references': ['https://garybadger.com/wp-content/uploads/2017/09/johnny-cash-ring-of-fire-trumpets.pdf',
                    'https://www.musicnotes.com/sheetmusic/johnny-cash/ring-of-fire/MN0298397'],
     'notes': score(RING_OF_FIRE_HOOK)*2}
]


def run_ffmpeg(ffmpeg, args, data=None):
    return subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", *args],
                          input=data, stdout=subprocess.PIPE, check=True).stdout


def frequency(name, transpose):
    letters = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    accidental = -1 if "b" in name else (1 if "#" in name else 0)
    midi = 12 * (int(name[-1]) + 1) + letters[name[0]] + accidental + transpose
    return 440 * 2 ** ((midi - 69) / 12)


def decode_source(ffmpeg, name, checksum):
    source = ROOT / "audio" / name
    assert hashlib.sha256(source.read_bytes()).hexdigest() == checksum, "Unexpected source recording"
    raw = run_ffmpeg(ffmpeg, ["-i", str(source), "-ac", "1", "-ar", str(SAMPLE_RATE),
                             "-f", "f32le", "pipe:1"])
    return np.frombuffer(raw, dtype="<f4").astype(np.float64)


def instrument_samples(ffmpeg):
    trumpet = decode_source(ffmpeg, "trumpeten.mp3", SOURCE_SHA256)
    wet = decode_source(ffmpeg, "blota.mp3", WET_SHA256)
    # Preserve a complete recorded attack/body/tail, not a repeating wavetable.
    core = trumpet[round(1.49*SAMPLE_RATE):round(1.94*SAMPLE_RATE)].copy()
    wet = wet[:round(0.67*SAMPLE_RATE)].copy()
    core -= np.mean(core)
    wet -= np.mean(wet)
    return core, wet, 250.873629


def sample_playback(sample, positions):
    # Zero beyond the original recording: neither source is looped or tiled.
    return np.interp(positions, np.arange(len(sample)), sample, left=0, right=0)


def note_audio(core, wet, base_hz, hz, duration, index, tight_attacks=None):
    count = max(1, round(duration * SAMPLE_RATE))
    time = np.arange(count) / SAMPLE_RATE
    if tight_attacks is not None:
        # Alternate two real fart attacks, without random timing or wet tails
        # masking the sixteenth-note pulse. The same pitched body carries the
        # melody on both articulations, so changing attacks cannot change notes.
        texture = sample_playback(tight_attacks[index % 2], time*SAMPLE_RATE)
        texture *= np.maximum(0, 1-time/0.045)**0.65
        body = sample_playback(core, time*SAMPLE_RATE*(hz/base_hz))
        attack = np.minimum(time/0.0015, 1)
        release = np.clip((duration-time)/0.008, 0, 1)
        return (texture*0.20 + body*1.35)*attack*release
    # The wet recording leads every note. Its variations remain at their natural
    # pitch and almost their original speed, including the irregular bubbling.
    wet_offsets = [0.0, 0.038, 0.011, 0.072, 0.022, 0.095, 0.048]
    wet_rates = [0.98, 1.025, 0.95, 1.01, 1.045, 0.97, 1.0]
    offset = wet_offsets[index % len(wet_offsets)]
    wet_rate = wet_rates[(index*3) % len(wet_rates)]
    texture = sample_playback(wet, (time*wet_rate+offset)*SAMPLE_RATE)
    # Compress only the unusually sharp recorded wet transients. This preserves
    # real splutters without letting a few spikes drown the melodic body.
    texture = 0.72*np.tanh(texture*3.2)
    # A full unlooped fart is repitched for the melodic body, arriving 18 ms after
    # the wet attack. All its natural pitch scoops and decay remain in the file.
    body = sample_playback(core, (time-0.018)*SAMPLE_RATE*(hz/base_hz))
    body_gain = [0.58, 0.62, 0.54, 0.60, 0.56, 0.64, 0.59][index % 7]
    result = texture + body*body_gain
    attack = np.minimum(time / 0.003, 1)
    release = np.minimum((duration-time) / min(0.055, duration*0.28), 1)
    envelope = np.maximum(0, attack * release)
    return result*envelope


def render(song, core, wet, base_hz, tight_attacks=None):
    seconds_per_beat = 60 / song["bpm"]
    total = sum(beats for _, beats in song["notes"]) * seconds_per_beat
    output = np.zeros(round((total+0.2) * SAMPLE_RATE))
    position = 0.04
    onsets = []
    for index, (name, beats) in enumerate(song["notes"]):
        span = beats * seconds_per_beat
        if name != "R":
            pitches = [frequency(pitch, song["transpose"]) for pitch in name.split("+")]
            # Long written notes end in an organic recorded tail, rather than
            # sustaining a perfectly even tone for the entire note duration.
            tight = song.get('articulation') == 'tight-alternating'
            if tight:
                assert tight_attacks is not None, 'Alternating fart attacks required'
            gate = min(0.12, span*0.67) if tight else min(0.72, max(0.065, span-min(0.035, span*0.08)))
            note = note_audio(core, wet, base_hz, pitches[0], gate, index,
                              tight_attacks if tight else None)
            if len(pitches) > 1:
                # The wet layer is identical in every voice, so averaging keeps
                # that real texture unchanged and blends the pitched fart bodies.
                note = sum(note_audio(core, wet, base_hz, hz, gate, index)
                           for hz in pitches) / len(pitches)
            start = round(position*SAMPLE_RATE)
            output[start:start+len(note)] += note
            onsets.append(dict(note=name, rendered_frequency_hz=[round(hz, 4) for hz in pitches],
                               start_seconds=round(position, 6), length_seconds=round(gate, 6)))
        position += span
    peak = float(np.max(np.abs(output)))
    output *= 0.79 / peak
    return output, onsets


def validate_mp3(ffmpeg, path, onsets):
    raw = run_ffmpeg(ffmpeg, ["-i", str(path), "-ac", "1", "-ar", str(SAMPLE_RATE),
                             "-f", "f32le", "pipe:1"])
    decoded = np.frombuffer(raw, dtype="<f4").astype(float)
    assert len(decoded) > SAMPLE_RATE*10, "Song too short"
    peak = float(np.max(np.abs(decoded)))
    assert 0.1 < peak < 0.99, "Empty or clipping audio"
    # Every note must have an audible attack in the final mixed file. The wet
    # layer is deliberately unpitched and retains natural pitch fluctuation;
    # measuring it as an ideal sine-like note would give misleading results.
    attacks = [decoded[round(item["start_seconds"]*SAMPLE_RATE):
                       round((item["start_seconds"]+min(0.09,item["length_seconds"]))*SAMPLE_RATE)]
               for item in onsets]
    attack_rms = [float(np.sqrt(np.mean(a*a))) for a in attacks]
    assert min(attack_rms) > 0.012, "Inaudible recorded fart attack"
    return dict(duration_seconds=round(len(decoded)/SAMPLE_RATE, 4),
                peak=round(peak, 6), rms=round(float(np.sqrt(np.mean(decoded**2))), 6),
                clipping_samples=int(np.sum(np.abs(decoded) >= 1)),
                audible_recorded_attacks=len(attacks),
                minimum_attack_rms=round(min(attack_rms), 6),
                bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--audition", type=Path,
                        help="Render only the first 8 seconds of the first song to this MP3; leave app assets untouched")
    parser.add_argument("--only", nargs="+", choices=[song["id"] for song in SONGS],
                        help="Regenerate only these songs and their metadata, preserving the other MP3 files exactly")
    args = parser.parse_args()
    output_dir = ROOT / "audio/songs"
    output_dir.mkdir(parents=True, exist_ok=True)
    core, wet, base_hz = instrument_samples(args.ffmpeg)
    tight_attacks = None
    if not args.audition and (not args.only or 'sandstorm' in args.only):
        short = decode_source(args.ffmpeg, 'snabbisen.mp3', SHORT_SHA256)
        def short_attack(recording):
            # Use the loudest 30 ms block in the first 300 ms; never loop it.
            block = round(0.03*SAMPLE_RATE)
            chunks = recording[:10*block].reshape(-1, block)
            start = int(np.argmax(np.mean(chunks**2, axis=1)))*block
            clip = recording[start:start+round(0.045*SAMPLE_RATE)].copy()
            clip -= np.mean(clip)
            return clip*(0.8/np.max(np.abs(clip)))
        tight_attacks = (short_attack(wet), short_attack(short))
    if args.audition:
        audio, _ = render(SONGS[0], core, wet, base_hz)
        run_ffmpeg(args.ffmpeg, ["-y", "-f", "f32le", "-ar", str(SAMPLE_RATE), "-ac", "1",
                   "-i", "pipe:0", "-c:a", "libmp3lame", "-b:a", "96k", str(args.audition)],
                   audio[:8*SAMPLE_RATE].astype("<f4").tobytes())
        print(args.audition)
        return
    metadata = dict(instrument=dict(file="audio/trumpeten.mp3", sha256=SOURCE_SHA256,
                    title="fart,bum,trumpet,poop.wav", author="sorce", license="CC0-1.0",
                    source_page="https://freesound.org/people/sorce/sounds/431621/",
                    sample=dict(start_seconds=1.49, end_seconds=1.94,
                                base_frequency_hz=base_hz, looped=False)),
                    wet_instrument=dict(file="audio/blota.mp3", sha256=WET_SHA256,
                    title="Diarrhea", author="Breviceps", license="CC0-1.0",
                    source_page="https://freesound.org/people/Breviceps/sounds/445997/",
                    sample=dict(start_seconds=0, end_seconds=0.67, looped=False)),
                    articulation="Unlooped recorded fart articulation and repitched fart body; Sandstorm uses short alternating Blota/Snabbisen attacks; other songs retain natural wet scoops and decay",
                    format=dict(codec="mp3", mime="audio/mpeg", sample_rate=SAMPLE_RATE,
                                channels=1, bitrate_kbps=96), songs=[])
    prior = {}
    metadata_path = output_dir / "metadata.json"
    prior_metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    if args.only:
        prior = {song["id"]: song for song in prior_metadata["songs"]}
    for song in SONGS:
        if args.only and song["id"] not in args.only:
            previous = prior[song["id"]]
            assert hashlib.sha256((ROOT / previous["file"]).read_bytes()).hexdigest() == previous["validation"]["sha256"], "Existing song changed"
            metadata["songs"].append(previous)
            continue
        audio, onsets = render(song, core, wet, base_hz, tight_attacks)
        path = output_dir / (song["id"]+".mp3")
        run_ffmpeg(args.ffmpeg, ["-y", "-f", "f32le", "-ar", str(SAMPLE_RATE), "-ac", "1",
                   "-i", "pipe:0", "-c:a", "libmp3lame", "-b:a", "96k", "-id3v2_version", "3",
                   "-metadata", "title="+song["title"], "-metadata", "artist=Fart Machine",
                   "-metadata", "comment=Wet sampled-fart melody: CC0 recordings by sorce and Breviceps",
                   str(path)], audio.astype("<f4").tobytes())
        report = validate_mp3(args.ffmpeg, path, onsets)
        metadata["songs"].append({k: v for k, v in song.items() if k != "notes"} |
            dict(file="audio/songs/"+path.name,
                 arrangement=song.get("arrangement", "Two complete melody verses" if song["id"] == "baby-shark" else "One complete melody verse")
                 + ("; no voice or accompaniment" if song.get('articulation') == 'tight-alternating' else " with wet recorded fart articulation; no voice or accompaniment"),
                 notes=[dict(note=n, beats=b) for n, b in song["notes"]], validation=report))
        print(f"{path.name}: {report['duration_seconds']} s, {report['bytes']} bytes, "
              f"peak {report['peak']}, {report['audible_recorded_attacks']} audible wet attacks", flush=True)
    managed_ids = {song['id'] for song in SONGS}
    for extra in prior_metadata.get('songs', []):
        if extra['id'] not in managed_ids:
            assert hashlib.sha256((ROOT / extra['file']).read_bytes()).hexdigest() == extra['validation']['sha256'], 'Existing orchestra changed'
            metadata['songs'].append(extra)
    if 'orchestra_format' in prior_metadata:
        metadata['orchestra_format'] = prior_metadata['orchestra_format']
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
