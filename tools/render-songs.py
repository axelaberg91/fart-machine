#!/usr/bin/env python3
"""Render the seven fart-song MP3 assets offline. Requires Python, NumPy and FFmpeg.

Run: python tools/render-songs.py --ffmpeg /path/to/ffmpeg
The website plays the finished files through native HTML audio; this tool is
never loaded by the app. All instrument audio comes from the unchanged CC0
recordings audio/trumpeten.mp3 and audio/blota.mp3. DragonForce's comic ending
also uses the unchanged CC0 recordings audio/katastrofen.mp3 and audio/vulkanen.mp3.
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
COLLAPSE_SOURCES = [
    dict(file="audio/katastrofen.mp3", title="Fart 3", author="Under7dude",
         license="CC0-1.0", source_page="https://freesound.org/people/Under7dude/sounds/163381/",
         sha256="b637625415830a5baa34b2db1dd2fd6da3f404670516db2aa6a753e157a2d56a"),
    dict(file="audio/vulkanen.mp3", title="Blubberfreak Fart 3", author="Blubberfreak",
         license="CC0-1.0", source_page="https://freesound.org/people/Blubberfreak/sounds/732057/",
         sha256="c90baedd94619d3d351e556f585dc56067ca9d1f976bfa6ce15f9240ff8a49f6")
]


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

DRAGONFORCE_MELODY = 'C4 D4 Eb4 C4 D4 Eb4 F4 Eb4 G4 Eb4 F4 D4 Eb4 C4 D4 Bb3'
# The published acoustic guitar line places a G3 sixteenth between every
# melody sixteenth. One two-bar loop lasts 2.4 seconds at 200 BPM.
DRAGONFORCE_INTRO = [(note, .25) for melody in DRAGONFORCE_MELODY.split()
                    for note in (melody, 'G3')]

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
    {'id': 'through-the-fire-and-flames',
     'title': 'Through the Fire and Flames',
     'bpm': 200,
     'transpose': 0,
     'meter': '4/4',
     'melody': 'Through the Fire and Flames — DragonForce; Sam Totman, ZP Theart, '
               'Vadim Pruzhanov and Herman Li (Inhuman Rampage, 2006)',
     'composition_rights': 'Copyrighted composition; CC0 applies only to the source fart recordings',
     'render_mode': 'guitar_attempt_comedy',
     'arrangement': 'Ten-second comic performance: one 2.4-second faithful rapid guitar-intro hook; '
                    'a faster attempt increasingly '
                    'stutters and slips in pitch, loses momentum, gives up in silence, and '
                    'ends in a longer wet recorded-fart collapse',
     'source_notation': 'mySongBook published acoustic-guitar preview: two-bar sixteenth-note '
                        'figure with G3 between the sixteen melody notes, played once. '
                        'The melody also matches Technical Guitar / kiso-ren published notation. '
                        'Sounding G3–G4 register and published 200 BPM retained',
     'reference_validation': 'Two independent visual readings agree on the melody, recurring '
                             'G3 and sixteenth-note timing. The official Apple preview confirms '
                             'C-minor pitch material but contains a later mixed section; exact '
                             'intro timing follows the published acoustic notation. All timing '
                             'errors and pitch slides after the opening are intentional comedy',
     'references': ['https://www.guitar-pro.com/tabs/t/3864-through-the-fire-and-flames',
                    'https://www.mymusic5.com/technicalguitar/181763',
                    'https://dragonforce.com/release/inhuman-rampage/',
                    'https://music.apple.com/us/song/1679612971',
                    'https://www.youtube.com/watch?v=XkFz_hi2tWY'],
     'notes': DRAGONFORCE_INTRO}
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
            pitches = [frequency(pitch, song["transpose"]) for pitch in name.split("+")]
            # Long written notes end in an organic recorded tail, rather than
            # sustaining a perfectly even tone for the entire note duration.
            gate = min(0.72, max(0.065, span-min(0.035, span*0.08)))
            note = note_audio(core, wet, base_hz, pitches[0], gate, index)
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


def slipping_note_audio(core, wet, base_hz, hz, duration, index, bend):
    """Pitch-slide a recorded body; the wet recording remains at natural pitch."""
    if bend == 0:
        return note_audio(core, wet, base_hz, hz, duration, index)
    count = max(1, round(duration*SAMPLE_RATE))
    time = np.arange(count)/SAMPLE_RATE
    texture = note_audio(np.zeros_like(core), wet, base_hz, hz, duration, index)
    # Integrate changing sample-playback rates. There is no oscillator, repeated
    # waveform or generated instrument under the real recorded fart body.
    rates = (hz/base_hz)*2**(np.linspace(0, bend, count)/12)
    positions = np.cumsum(rates)-rates[0]-(.018*SAMPLE_RATE*hz/base_hz)
    body = sample_playback(core, positions)
    gain = [0.58, 0.62, 0.54, 0.60, 0.56, 0.64, 0.59][index % 7]
    envelope = np.maximum(0, np.minimum(time/.003, 1)*
                          np.minimum((duration-time)/min(.055, duration*.28), 1))
    return texture+body*gain*envelope


def render_dragonforce(song, core, wet, base_hz, ffmpeg):
    """The new song's comic progression; the other six renderers stay unchanged."""
    clean, onsets = render(song, core, wet, base_hz)
    clean_end = .04+sum(beats for _, beats in song['notes'])*60/song['bpm']
    assert abs(clean_end-2.44) < .000001, 'Verified two-bar opening must last 2.4 seconds'
    strained_start, strained_end = 2.50, 5.15
    slipping_end = 6.00
    collapse_start, collapse_end = 6.45, 9.76
    output = np.zeros(10*SAMPLE_RATE)
    output[:len(clean)] = clean
    for event in onsets:
        event['stage'] = 'faithful_hook'
        event['kind'] = 'melody_note'
        event['bend_semitones'] = 0

    def add_note(name, start, duration, index, stage, bend=0):
        hz = frequency(name, song['transpose'])
        note = slipping_note_audio(core, wet, base_hz, hz, duration, index, bend)
        offset = round(start*SAMPLE_RATE)
        output[offset:offset+len(note)] += note
        onsets.append(dict(note=name, kind='melody_note', stage=stage,
                           rendered_frequency_hz=[round(hz, 4)],
                           start_seconds=round(start, 6), length_seconds=round(duration, 6),
                           bend_semitones=round(bend, 4)))

    position, index = strained_start, 0
    jitter = [0, .009, -.006, .018, -.003, .004, -.009]
    bends = [0, .6, -.9, 1.5, -2.2, .3, -1.1]
    while position < strained_end-.04:
        progress = (position-strained_start)/(strained_end-strained_start)
        name, beats = song['notes'][index % len(song['notes'])]
        # Start faster, progressively rush, insert audible hesitations and
        # interrupt selected notes with tight recorded-fart stammers.
        pulse = beats*60/song['bpm']/(1.12+.38*progress)
        if index % 19 == 13:
            position += .07+.07*progress
        if position >= strained_end-.04:
            break
        repetitions = 3 if index % 17 == 9 else 1
        for repeat in range(repetitions):
            if position >= strained_end-.04:
                break
            duration = min(.065 if repetitions == 1 else .037,
                           strained_end-position)
            bend = bends[(index+repeat) % len(bends)]*(.25+progress)
            add_note(name, position, duration, index+128+repeat, 'stressed_attempt', bend)
            position += (.033 if repetitions > 1 else
                         max(.038, pulse+jitter[index % len(jitter)]*progress))
        index += 1

    # A few last notes drag down, followed by one completely quiet surrender.
    last_notes = [song['notes'][i][0] for i in (0, 4, 12)]
    for index, (name, offset, duration, bend) in enumerate(zip(
            last_notes, [0, .15, .36], [.12, .17, .40], [-3, -7, -12])):
        add_note(name, strained_end+offset, duration, index+333, 'pitch_collapse', bend)

    recordings = {'blota.mp3': decode_source(ffmpeg, 'blota.mp3', WET_SHA256)}
    for source in COLLAPSE_SOURCES:
        name = Path(source['file']).name
        recordings[name] = decode_source(ffmpeg, name, source['sha256'])
    # Each event plays an unlooped real recording excerpt. The long catastrophe
    # is surrounded by irregular wet splutters, with no voice or accompaniment.
    splutters = [
        ('blota.mp3', 0, 0, .55, .90, .63),
        ('vulkanen.mp3', .25, .89, .61, 1, .70),
        ('katastrofen.mp3', .40, 0, 2.55, 1.04, .72),
        ('blota.mp3', .60, .10, .35, 1.10, .54),
        ('blota.mp3', 1.15, .03, .55, .95, .56),
        ('vulkanen.mp3', 1.75, .89, .53, .90, .62),
        ('katastrofen.mp3', 2.10, 1.20, .75, 1.05, .55),
        ('blota.mp3', 2.50, 0, .48, .70, .60)
    ]
    for name, offset, source_start, source_duration, rate, gain in splutters:
        duration = source_duration/rate
        time = np.arange(round(duration*SAMPLE_RATE))/SAMPLE_RATE
        audio = sample_playback(recordings[name], (source_start+time*rate)*SAMPLE_RATE)
        audio -= np.mean(audio)
        audio = gain*np.tanh(audio*2.2)
        envelope = np.minimum(time/.004, 1)*np.minimum((duration-time)/.04, 1)
        audio *= np.maximum(envelope, 0)
        start = collapse_start+offset
        output_offset = round(start*SAMPLE_RATE)
        output[output_offset:output_offset+len(audio)] += audio
        onsets.append(dict(note='recorded wet collapse', kind='recorded_fart',
                           stage='wet_collapse', source_file='audio/'+name,
                           source_start_seconds=source_start, source_duration_seconds=source_duration,
                           playback_rate=rate, gain=gain,
                           start_seconds=round(start, 6), length_seconds=round(duration, 6)))
    # End with a clean decay, then exact digital silence before the ten-second
    # deadline. No sample is abruptly truncated by the exported file boundary.
    fade_start, fade_end = round(9.60*SAMPLE_RATE), round(9.94*SAMPLE_RATE)
    output[fade_start:fade_end] *= np.linspace(1, 0, fade_end-fade_start)
    output[fade_end:] = 0
    output *= .77/np.max(np.abs(output))
    stages = [
        dict(id='faithful_hook', start_seconds=.04, end_seconds=round(clean_end, 6),
             description='Verified guitar-intro notes and sixteenth pulse at 200 BPM'),
        dict(id='stressed_attempt', start_seconds=round(strained_start, 6),
             end_seconds=round(strained_end, 6),
             description='Faster reprise with increasingly irregular timing, stammers and pitch slips'),
        dict(id='pitch_collapse', start_seconds=round(strained_end, 6),
             end_seconds=round(slipping_end, 6),
             description='Dragging final attempts and recorded-note pitch slides down'),
        dict(id='giving_up_pause', start_seconds=round(slipping_end, 6),
             end_seconds=round(collapse_start, 6), description='Completely silent surrender'),
        dict(id='wet_collapse', start_seconds=round(collapse_start, 6),
             end_seconds=round(collapse_end, 6),
             description='Long layered real wet farts, including Katastrofen, Vulkanen and Blöta')
    ]
    return output, onsets, stages


def validate_mp3(ffmpeg, path, onsets):
    raw = run_ffmpeg(ffmpeg, ["-i", str(path), "-ac", "1", "-ar", str(SAMPLE_RATE),
                             "-f", "f32le", "pipe:1"])
    decoded = np.frombuffer(raw, dtype="<f4").astype(float)
    assert len(decoded) >= SAMPLE_RATE*10, "Song too short"
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
                    additional_instruments=COLLAPSE_SOURCES,
                    format=dict(codec="mp3", mime="audio/mpeg", sample_rate=SAMPLE_RATE,
                                channels=1, bitrate_kbps=96), songs=[])
    prior = {}
    if args.only:
        prior_metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
        prior = {song["id"]: song for song in prior_metadata["songs"]}
    for song in SONGS:
        if args.only and song["id"] not in args.only:
            previous = prior[song["id"]]
            assert hashlib.sha256((ROOT / previous["file"]).read_bytes()).hexdigest() == previous["validation"]["sha256"], "Existing song changed"
            metadata["songs"].append(previous)
            continue
        stages = []
        if song.get('render_mode') == 'guitar_attempt_comedy':
            audio, onsets, stages = render_dragonforce(song, core, wet, base_hz, args.ffmpeg)
        else:
            audio, onsets = render(song, core, wet, base_hz)
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
                 + " with wet recorded fart articulation; no voice or accompaniment",
                 notes=[dict(note=n, beats=b) for n, b in song["notes"]], validation=report) |
                 (dict(stages=stages, performance_events=onsets,
                       additional_source_files=[source['file'] for source in COLLAPSE_SOURCES])
                  if stages else {}))
        print(f"{path.name}: {report['duration_seconds']} s, {report['bytes']} bytes, "
              f"peak {report['peak']}, {report['audible_recorded_attacks']} audible wet attacks", flush=True)
    (output_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
