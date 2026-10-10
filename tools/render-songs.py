#!/usr/bin/env python3
"""Render the six fart-song MP3 assets offline. Requires Python, NumPy and FFmpeg.

Run: python tools/render-songs.py --ffmpeg /path/to/ffmpeg
The website plays the finished files through native HTML audio; this tool is
never loaded by the app. All instrument audio comes from audio/trumpeten.mp3.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RATE = 44100
SOURCE_SHA256 = "cf58ca41e3b6fb183995a099bc88e084df3561110aefc40ee9f9040cbd815c63"


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


def instrument_sample(ffmpeg):
    source = ROOT / "audio/trumpeten.mp3"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256, "Unexpected source recording"
    raw = run_ffmpeg(ffmpeg, ["-i", str(source), "-ac", "1", "-ar", str(SAMPLE_RATE),
                             "-f", "f32le", "pipe:1"])
    audio = np.frombuffer(raw, dtype="<f4").astype(np.float64)
    # This real recorded fart has a clearly periodic section at about 250 Hz.
    # Use a measured, phase-aligned multi-cycle loop so sustained notes retain the
    # original waveform and variation rather than adding a synthesized tone.
    region = audio[round(1.59 * SAMPLE_RATE):round(1.75 * SAMPLE_RATE)]
    crossing = np.where((region[:-1] <= 0) & (region[1:] > 0))[0]
    # Strong positive-going crossings once per fundamental period. Other tiny
    # crossings in the same cycle are rejected with a 3 ms refractory interval.
    selected = []
    for i in crossing:
        if region[i+1:min(len(region), i+30)].max(initial=0) > 0.22:
            if not selected or i-selected[-1] > 0.003 * SAMPLE_RATE:
                selected.append(int(i))
    candidates = [(a, b) for a in selected for b in selected if
                  0.09 * SAMPLE_RATE < b-a < 0.13 * SAMPLE_RATE]
    start, end = min(candidates, key=lambda pair:
                     np.mean((region[pair[0]:pair[0]+90]-region[pair[1]:pair[1]+90])**2))
    loop = region[start:end].copy()
    periods = round(len(loop) / (SAMPLE_RATE / 250))
    base_hz = periods * SAMPLE_RATE / len(loop)
    loop -= np.mean(loop)
    # A short phase-aligned overlap hides the join while retaining the recording.
    fade = min(64, len(loop)//12)
    blend = np.linspace(0, 1, fade)
    seam = loop[-fade:] * (1-blend) + loop[:fade] * blend
    loop[-fade:] = seam
    return loop, base_hz, {"start_seconds": round(1.59+start/SAMPLE_RATE, 6),
                           "end_seconds": round(1.59+end/SAMPLE_RATE, 6),
                           "base_frequency_hz": round(base_hz, 6), "cycles": periods}


def note_audio(loop, base_hz, hz, duration, index):
    count = max(1, round(duration * SAMPLE_RATE))
    rate = hz / base_hz
    # Sample playback-rate transposition, with the sustained portion looped.
    position = (np.arange(count) * rate) % len(loop)
    result = np.interp(position, np.arange(len(loop)+1), np.r_[loop, loop[0]])
    time = np.arange(count) / SAMPLE_RATE
    attack = np.minimum(time / 0.012, 1)
    release = np.minimum((duration-time) / min(0.075, duration*0.3), 1)
    # A slight breath-like amplitude fall gives every recorded fart a clear onset.
    envelope = np.maximum(0, attack * release) * (0.68 + 0.32*np.exp(-time/0.11))
    return result * envelope * (0.96 if index % 4 else 1.0)


def render(song, loop, base_hz):
    seconds_per_beat = 60 / song["bpm"]
    total = sum(beats for _, beats in song["notes"]) * seconds_per_beat
    output = np.zeros(round((total+0.2) * SAMPLE_RATE))
    position = 0.04
    onsets = []
    for index, (name, beats) in enumerate(song["notes"]):
        span = beats * seconds_per_beat
        if name != "R":
            hz = frequency(name, song["transpose"])
            gate = max(0.065, span-min(0.04, span*0.10))
            note = note_audio(loop, base_hz, hz, gate, index)
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
    max_cents = 0
    for item in onsets:
        start = round((item["start_seconds"]+0.04)*SAMPLE_RATE)
        length = round(min(0.11, item["length_seconds"]-0.055)*SAMPLE_RATE)
        if length < 1000:
            continue
        x = decoded[start:start+length]
        x -= np.mean(x)
        corr = np.correlate(x, x, mode="full")[len(x)-1:]
        target_period = SAMPLE_RATE / item["rendered_frequency_hz"]
        lower, upper = round(target_period*0.91), round(target_period*1.09)
        lag = lower + int(np.argmax(corr[lower:upper+1]))
        # Subsample interpolation makes the measurement meaningful at high notes.
        a, b, c = corr[lag-1:lag+2]
        fractional_lag = lag + 0.5*(a-c)/(a-2*b+c)
        measured = SAMPLE_RATE/fractional_lag
        max_cents = max(max_cents, abs(1200*math.log2(measured/item["rendered_frequency_hz"])))
    assert max_cents < 35, f"Pitch drift too large: {max_cents} cents"
    return dict(duration_seconds=round(len(decoded)/SAMPLE_RATE, 4),
                peak=round(peak, 6), rms=round(float(np.sqrt(np.mean(decoded**2))), 6),
                clipping_samples=int(np.sum(np.abs(decoded) >= 1)),
                max_note_pitch_error_cents=round(max_cents, 3),
                bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    output_dir = ROOT / "audio/songs"
    output_dir.mkdir(parents=True, exist_ok=True)
    loop, base_hz, sample = instrument_sample(args.ffmpeg)
    metadata = dict(instrument=dict(file="audio/trumpeten.mp3", sha256=SOURCE_SHA256,
                    title="fart,bum,trumpet,poop.wav", author="sorce", license="CC0-1.0",
                    source_page="https://freesound.org/people/sorce/sounds/431621/", sample=sample),
                    format=dict(codec="mp3", mime="audio/mpeg", sample_rate=SAMPLE_RATE,
                                channels=1, bitrate_kbps=96), songs=[])
    for song in SONGS:
        audio, onsets = render(song, loop, base_hz)
        path = output_dir / (song["id"]+".mp3")
        run_ffmpeg(args.ffmpeg, ["-y", "-f", "f32le", "-ar", str(SAMPLE_RATE), "-ac", "1",
                   "-i", "pipe:0", "-c:a", "libmp3lame", "-b:a", "96k", "-id3v2_version", "3",
                   "-metadata", "title="+song["title"], "-metadata", "artist=Fart Machine",
                   "-metadata", "comment=Melody played on the CC0 fart recording by sorce",
                   str(path)], audio.astype("<f4").tobytes())
        report = validate_mp3(args.ffmpeg, path, onsets)
        metadata["songs"].append({k: v for k, v in song.items() if k != "notes"} |
            dict(file="audio/songs/"+path.name, arrangement="One complete melody verse, solo sampled fart; no voice or accompaniment",
                 notes=[dict(note=n, beats=b) for n, b in song["notes"]], validation=report))
        print(f"{path.name}: {report['duration_seconds']} s, {report['bytes']} bytes, "
              f"peak {report['peak']}, pitch error <= {report['max_note_pitch_error_cents']} cents", flush=True)
    (output_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
