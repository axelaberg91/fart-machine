#!/usr/bin/env python3
"""Render the six fart-song MP3 assets offline. Requires Python, NumPy and FFmpeg.

Run: python tools/render-songs.py --ffmpeg /path/to/ffmpeg
The website plays the finished files through native HTML audio; this tool is
never loaded by the app. All instrument audio comes from the unchanged CC0
recordings audio/trumpeten.mp3 and audio/blota.mp3.
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


def score(text):
    """Space-separated note:beat tokens; R is a rest."""
    return [(token.split(":")[0], float(token.split(":")[1])) for token in text.split()]


TWINKLE_A = "C4:1 C4:1 G4:1 G4:1 A4:1 A4:1 G4:2 F4:1 F4:1 E4:1 E4:1 D4:1 D4:1 C4:2"
TWINKLE_B = "G4:1 G4:1 F4:1 F4:1 E4:1 E4:1 D4:2"
BA_A = "F4:1 C5:1 A4:0.5 A4:0.5 F4:1 G4:0.5 G4:0.5 C4:0.5 C4:0.5 F4:1 R:1"
BROTHER_A = "C4:1 D4:1 E4:1 C4:1"
BROTHER_B = "E4:1 F4:1 G4:2"
BROTHER_C = "G4:0.5 A4:0.5 G4:0.5 F4:0.5 E4:1 C4:1"
BROTHER_D = "C4:1 G3:1 C4:2"
BEAR_A = "C4:1 C4:1 C4:1 E4:1 D4:1 D4:1 D4:1 F4:1 E4:1 E4:1 D4:1 D4:1 C4:4"
LONDON_A = "G4:1.5 A4:0.5 G4:1 F4:1 E4:1 F4:1 G4:2"

SONGS = [
    dict(id="blinka-lilla-stjarna", title="Blinka lilla stjärna", bpm=138,
         transpose=-5, meter="4/4", melody="Traditional: Ah! vous dirai-je, maman",
         notes=score(" ".join([TWINKLE_A, TWINKLE_B, TWINKLE_B, TWINKLE_A])),
         references=["https://ciss.se/munspel/barnvisor.html"]),
    dict(id="ba-ba-vita-lamm", title="Bä bä vita lamm", bpm=104,
         transpose=-10, meter="2/4", melody="Alice Tegnér, Sjung med oss, mamma! (1892), no. 5",
         notes=score(" ".join([BA_A, BA_A,
             "D5:0.5 Bb4:0.5 Bb4:0.5 Bb4:0.5 C5:1.5 A4:0.5",
             "Bb4:0.5 G4:0.5 G4:0.5 G4:0.5 A4:1.5 F4:0.5",
             "D5:1 Bb4:1 C5:1 A4:0.5 A4:0.5 Bb4:0.5 E4:0.5 E4:0.5 E4:0.5 F4:1 R:1"])),
         references=["https://runeberg.org/sjungmamma/1/0010.html",
                     "https://runeberg.org/sjungmamma/1/0011.html",
                     "https://www.spelapiano.org/noter/ba-ba-vita-lamm.html"]),
    dict(id="broder-jakob", title="Broder Jakob", bpm=116,
         transpose=-5, meter="4/4", melody="Traditional: Frère Jacques",
         notes=score(" ".join([BROTHER_A, BROTHER_A, BROTHER_B, BROTHER_B,
                               BROTHER_C, BROTHER_C, BROTHER_D, BROTHER_D])),
         references=["https://www.skolesaga.no/musikk-8/musikk-8-1-1"]),
    dict(id="imse-vimse-spindel", title="Imse vimse spindel", bpm=300,
         transpose=-5, meter="6/8 (tempo counts eighth notes)", melody="Traditional: Itsy Bitsy Spider",
         notes=score("G3:1 C4:2 C4:1 C4:2 D4:1 E4:3 E4:2 E4:1 D4:2 C4:1 D4:2 E4:1 C4:6 "
                     "E4:3 E4:2 F4:1 G4:3 G4:3 F4:2 E4:1 F4:2 G4:1 E4:6 "
                     "C4:3 C4:2 D4:1 E4:3 E4:3 D4:2 C4:1 D4:2 E4:1 C4:3 G3:2 G3:1 "
                     "C4:2 C4:1 C4:2 D4:1 E4:3 E4:2 E4:1 D4:2 C4:1 D4:2 E4:1 C4:5"),
         references=["https://www.bethsnotesplus.com/wp-content/uploads/2024/11/Itsy-Bitsy-Spider.pdf"]),
    dict(id="bjornen-sover", title="Björnen sover", bpm=138,
         transpose=-5, meter="4/4", melody="Traditional: Gubben Noak / Björnen sover",
         notes=score(" ".join([BEAR_A,
             "E4:1 E4:1 E4:1 E4:1 G4:2 F4:2 D4:1 D4:1 D4:1 D4:1 F4:2 E4:2", BEAR_A])),
         references=["https://ciss.se/munspel/barnvisor.html"]),
    dict(id="london-bridge", title="London Bridge", bpm=120,
         transpose=-5, meter="4/4", melody="Traditional: London Bridge Is Falling Down",
         notes=score(" ".join([LONDON_A, "D4:1 E4:1 F4:2 E4:1 F4:1 G4:2", LONDON_A,
                               "D4:2 G4:2 E4:1 C4:3"])),
         references=["https://www.8notes.com/scores/18427.asp"]),
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


def note_audio(core, wet, base_hz, hz, duration, index):
    count = max(1, round(duration * SAMPLE_RATE))
    time = np.arange(count) / SAMPLE_RATE
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


def render(song, core, wet, base_hz):
    seconds_per_beat = 60 / song["bpm"]
    total = sum(beats for _, beats in song["notes"]) * seconds_per_beat
    output = np.zeros(round((total+0.2) * SAMPLE_RATE))
    position = 0.04
    onsets = []
    for index, (name, beats) in enumerate(song["notes"]):
        span = beats * seconds_per_beat
        if name != "R":
            hz = frequency(name, song["transpose"])
            # Long written notes end in an organic recorded tail, rather than
            # sustaining a perfectly even tone for the entire note duration.
            gate = min(0.72, max(0.065, span-min(0.035, span*0.08)))
            note = note_audio(core, wet, base_hz, hz, gate, index)
            start = round(position*SAMPLE_RATE)
            output[start:start+len(note)] += note
            onsets.append(dict(note=name, rendered_frequency_hz=round(hz, 4),
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
                        help="Render only the first 8 seconds of Blinka to this MP3; leave app assets untouched")
    args = parser.parse_args()
    output_dir = ROOT / "audio/songs"
    output_dir.mkdir(parents=True, exist_ok=True)
    core, wet, base_hz = instrument_samples(args.ffmpeg)
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
                    articulation="Unlooped wet recorded attack/body/tail on every note; full repitched recorded fart body with natural scoops and decay",
                    format=dict(codec="mp3", mime="audio/mpeg", sample_rate=SAMPLE_RATE,
                                channels=1, bitrate_kbps=96), songs=[])
    for song in SONGS:
        audio, onsets = render(song, core, wet, base_hz)
        path = output_dir / (song["id"]+".mp3")
        run_ffmpeg(args.ffmpeg, ["-y", "-f", "f32le", "-ar", str(SAMPLE_RATE), "-ac", "1",
                   "-i", "pipe:0", "-c:a", "libmp3lame", "-b:a", "96k", "-id3v2_version", "3",
                   "-metadata", "title="+song["title"], "-metadata", "artist=Fart Machine",
                   "-metadata", "comment=Wet sampled-fart melody: CC0 recordings by sorce and Breviceps",
                   str(path)], audio.astype("<f4").tobytes())
        report = validate_mp3(args.ffmpeg, path, onsets)
        metadata["songs"].append({k: v for k, v in song.items() if k != "notes"} |
            dict(file="audio/songs/"+path.name, arrangement="One complete melody verse with wet recorded fart articulation; no voice or accompaniment",
                 notes=[dict(note=n, beats=b) for n, b in song["notes"]], validation=report))
        print(f"{path.name}: {report['duration_seconds']} s, {report['bytes']} bytes, "
              f"peak {report['peak']}, {report['audible_recorded_attacks']} audible wet attacks", flush=True)
    (output_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
