#!/usr/bin/env python3
"""Render layered fart orchestras with a distinct groove for each song.

Requires Python, NumPy and FFmpeg. Scores and source attribution live beside
this file and in audio/sources.json. All audible material is recorded farts:
there are no oscillators, drum libraries, vocals or original song recordings.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SR = 44100
spec = importlib.util.spec_from_file_location('legacy_songs', ROOT/'tools/render-songs.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def ffmpeg_run(executable, args, data=None):
    return subprocess.run([executable, '-hide_banner', '-loglevel', 'error', *args],
                          input=data, stdout=subprocess.PIPE, check=True).stdout


def load_sources(ffmpeg):
    bank = {}
    sources = json.loads((ROOT/'audio/sources.json').read_text(encoding='utf-8'))
    for source in sources:
        path = ROOT/source['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
        raw = ffmpeg_run(ffmpeg, ['-i', str(path), '-f', 'f32le', '-ar', str(SR), '-ac', '1', 'pipe:1'])
        recording = np.frombuffer(raw, dtype='<f4').astype(float)
        recording -= np.mean(recording)
        bank[source['key']] = recording
    return bank, sources


def envelope(audio, attack=.004, release=.025):
    audio = audio.copy()
    n = len(audio)
    a, r = min(n, round(attack*SR)), min(n, round(release*SR))
    if a: audio[:a] *= np.linspace(0, 1, a)
    if r: audio[-r:] *= np.linspace(1, 0, r)
    return audio


def normalized(audio, rms=.18):
    audio = audio-np.mean(audio)
    return audio*(rms/max(1e-6, np.sqrt(np.mean(audio**2))))


def crop(bank, name, start, duration):
    return bank[name][round(start*SR):round((start+duration)*SR)].copy()


def natural_hit(bank, name, duration, rate=1.0, offset=0.0, bright=False, reverse=False):
    # Every articulation uses a finite recorded passage, never a repeating wave.
    source = bank[name]
    if reverse: source = source[::-1]
    # Trim only leading near-silence, retaining the recorded attack. Different
    # source files have different padding, which must not move a written beat.
    active = np.flatnonzero(np.abs(source) > np.max(np.abs(source))*.035)
    if len(active): source = source[max(0, int(active[0])-round(.002*SR)):]
    positions = (np.arange(round(duration*SR))*rate)+offset*SR
    result = np.interp(positions, np.arange(len(source)), source, left=0, right=0)
    if bright:
        # Remove slow body movement to create a crisp, still recognizably wet tick.
        result = result-np.convolve(result, np.ones(81)/81, mode='same')
    return envelope(normalized(result), .002, min(.04, duration*.25))


def pitched(sample, base_hz, note, duration, gain=1):
    hz = legacy.frequency(note, 0)
    positions = np.arange(round(duration*SR))*(hz/base_hz)
    audio = np.interp(positions, np.arange(len(sample)), sample, left=0, right=0)
    return envelope(audio, .004, min(.045, duration*.18))*gain


class Orchestra:
    def __init__(self, score, bank, ffmpeg):
        self.score, self.bank = score, bank
        self.style = score.get('style', 'arena-rock' if score['id'] == 'the-final-countdown' else 'march')
        self.spb = 60/score['bpm']
        self.beats = score.get('total_beats', score['bars']*4)
        self.length = round((self.beats*self.spb+1.2)*SR)
        self.stems = {}
        self.events = []
        self.ffmpeg = ffmpeg
        self.long_notes = {}
        self.trumpet = normalized(crop(bank, 'trumpeten', 1.49, .45), .23)
        self.direct_trumpet = normalized(crop(bank, 'trumpeten', 1.54, .40), .23)
        self.bass = normalized(crop(bank, 'smygaren', .20, .46), .22)
        self.duck = normalized(crop(bank, 'ankan', .08, .27), .17)

    def sustained_lead(self, note, duration, direct_attack=False):
        key = (note, round(duration, 5), direct_attack)
        if key not in self.long_notes:
            hz = legacy.frequency(note, 0)
            sample = self.direct_trumpet if direct_attack else self.trumpet
            natural_duration = len(sample)/SR*250.873629/hz
            raw = pitched(sample, 250.873629, note, natural_duration)
            if duration > natural_duration*1.08:
                # Time-stretch one finite recording with FFmpeg's overlap-add
                # tempo filter; no oscillator, repeating wavetable or new tone.
                tempo = natural_duration/(duration+.025)
                factors = []
                while tempo < .5:
                    factors.append(.5); tempo /= .5
                factors.append(tempo)
                filters = ','.join('atempo='+str(factor) for factor in factors)
                data = ffmpeg_run(self.ffmpeg, ['-f', 'f32le', '-ar', str(SR), '-ac', '1',
                    '-i', 'pipe:0', '-af', filters, '-f', 'f32le', 'pipe:1'], raw.astype('<f4').tobytes())
                raw = np.frombuffer(data, dtype='<f4').astype(float)
            length = round(duration*SR)
            raw = np.pad(raw[:length], (0, max(0, length-len(raw))))
            self.long_notes[key] = envelope(raw, .004, min(.05, duration*.18))
        return self.long_notes[key].copy()

    def add(self, role, source, beat, audio, gain, pan=0, note=None):
        start = round((.04+beat*self.spb)*SR)
        if start >= self.length: return
        end = min(self.length, start+len(audio))
        if end <= start: return
        stem = self.stems.setdefault(role, np.zeros((self.length, 2)))
        # Equal-power panning with modest spread; downmix preserves the lead.
        angle = (pan+1)*np.pi/4
        levels = np.array([np.cos(angle), np.sin(angle)])
        # The supporting ensemble grows in the second half while the melody
        # stays at a stable level, giving the final phrase a larger sound.
        if role not in ('lead', 'lead-attacks'):
            gain *= .86 if beat < self.beats/2 else 1.12
        stem[start:end] += audio[:end-start, None]*levels*gain
        self.events.append(dict(role=role, source=source, beat=round(beat, 6),
                                note=note, start_seconds=round(start/SR, 6),
                                length_seconds=round((end-start)/SR, 6), gain=gain, pan=pan))

    def lead(self):
        if self.style not in ('arena-rock', 'march'):
            return self.groove_lead()
        fanfare = self.score['id'] == 'the-final-countdown'
        accents = ['blota', 'snabbisen', 'ankan', 'raketen'] if fanfare else ['kanonen', 'blota', 'snabbisen']
        for index, event in enumerate(self.score['melody']):
            beat, note, span = event['beat'], event['note'], event['duration']
            gate = min(1.4 if fanfare else 1.05, span*self.spb*.90)
            body = self.sustained_lead(note, gate)
            self.add('lead', 'trumpeten', beat, body, .92 if fanfare else 1.0, -.06, note)
            source = accents[index % len(accents)]
            attack = natural_hit(self.bank, source, min(.065, gate), rate=1.1, offset=.01)
            self.add('lead-attacks', source, beat, attack, .17, .07)
            # Brass-like octave doubling appears on phrase anchors; it leaves
            # enough room around fast notes for the melody to remain clear.
            if span >= .75:
                octave = note[:-1]+str(int(note[-1])-1)
                body = pitched(self.trumpet, 250.873629, octave, min(.7, gate*1.2))
                self.add('low-brass', 'trumpeten', beat+.018, body, .24, .25, octave)

    def harmonic_backing(self):
        if self.style not in ('arena-rock', 'march'):
            return self.groove_harmony()
        fanfare = self.score['id'] == 'the-final-countdown'
        for chord in self.score['chords']:
            start, length, notes = chord['beat'], chord['duration'], chord['notes']
            # Bass gallops for Europe; squared-off marching steps for Vader.
            offsets = np.arange(0, length, .5 if fanfare else 1.0)
            for i, offset in enumerate(offsets):
                note = notes[0] if i % 4 != 2 else notes[-1]
                while legacy.frequency(note, 0) > 125:
                    note = note[:-1]+str(int(note[-1])-1)
                duration = min(.28 if fanfare else .36, (length-offset)*self.spb*.8)
                audio = pitched(self.bass, 80.769, note, duration)
                self.add('bass', 'smygaren', start+float(offset), audio, .46 if fanfare else .56, 0, note)
            # Short three-note replies in a different fart timbre create harmony.
            for offset in np.arange(1 if fanfare else 0, length, 2):
                for voice, written in enumerate(notes[:3]):
                    note = written
                    while legacy.frequency(note, 0) < 145:
                        note = note[:-1]+str(int(note[-1])+1)
                    audio = pitched(self.duck, 82.276, note, .18 if fanfare else .23)
                    self.add('chords', 'ankan', start+float(offset), audio, .27, [-.45, .35, .15][voice], note)

    def rhythm(self):
        if self.style not in ('arena-rock', 'march'):
            return self.groove_rhythm()
        fanfare = self.score['id'] == 'the-final-countdown'
        for beat in range(int(self.beats)):
            if fanfare:
                if beat % 4 in (0, 2):
                    self.add('kick', 'kanonen', beat, natural_hit(self.bank, 'kanonen', .16, rate=.72), .45, -.10)
                else:
                    self.add('snare', 'blota', beat, natural_hit(self.bank, 'blota', .13, rate=1.3, bright=True), .34, .22)
                for offset in (0, .5):
                    if beat+offset < self.beats:
                        self.add('ticks', 'snabbisen', beat+offset, natural_hit(self.bank, 'snabbisen', .038, rate=1.8, offset=.14, bright=True), .10 if offset else .075, -.35 if offset else .35)
            else:
                # Strong downbeats plus a quiet, alternating military side roll.
                source = 'kanonen' if beat % 2 == 0 else 'katastrofen'
                self.add('march', source, beat, natural_hit(self.bank, source, .16, rate=.75), .39 if beat % 2 == 0 else .27, -.12)
                for j, offset in enumerate((.5, .75)):
                    source = 'snabbisen' if (beat+j) % 2 == 0 else 'blota'
                    self.add('roll', source, beat+offset, natural_hit(self.bank, source, .055, rate=1.4, offset=.08, bright=True), .09 if j else .14, .35 if j else -.35)
        # Phrase-end fills leave the lead upfront. Their sources, rate and
        # timing vary deterministically, so the result is reproducible.
        for phrase in range(8, int(self.beats)+1, 8):
            for j, offset in enumerate((-.75, -.5, -.25)):
                source = ('ankan', 'snabbisen', 'blota')[j]
                self.add('fills', source, phrase+offset, natural_hit(self.bank, source, .09, rate=1.1+j*.2), .24, (-1+j)*.4)
            if phrase < self.beats:
                audio = natural_hit(self.bank, 'raketen', .28, rate=1.2, reverse=True)
                self.add('riser', 'raketen', phrase-.55/self.spb, audio, .13, .45)

    def groove_lead(self):
        """Keep accepted melody timing/pitches; change accompaniment and colour."""
        dry = self.style in ('dance', 'trance')
        soft = self.style == 'lullaby'
        colours = ['ankan', 'snabbisen', 'blota', 'raketen']
        if self.style == 'trance': colours = ['blota', 'snabbisen']
        if self.style == 'heavy-rock': colours = ['kanonen', 'blota', 'snabbisen']
        for index, event in enumerate(self.score['melody']):
            beat, note, span = event['beat'], event['note'], event['duration']
            if self.style == 'trance':
                gate = min(.12, span*self.spb*.67)
            elif self.style == 'dance':
                gate = min(.48, span*self.spb*.77)
            elif self.style in ('playful', 'bouncy'):
                gate = min(.62, span*self.spb*.84)
            else:
                gate = min(1.15, span*self.spb*(.94 if soft else .87))
            # Starting at the voiced body avoids a slow pre-attack when the
            # accepted low G#2/B2 dance register slows the source recording.
            body = self.sustained_lead(note, gate, direct_attack=True)
            self.add('lead', 'trumpeten', beat, body, 1.0, -.04, note)
            source = colours[index % len(colours)]
            attack = natural_hit(self.bank, source, min(.05 if dry else .07, gate),
                                 rate=1.25 if dry else 1.0, offset=.015)
            self.add('lead-attacks', source, beat, attack, .10 if soft else .20, .07)
            # A lower brass response colours anchors without doubling every note.
            if not soft and span >= (1.5 if dry else 1):
                octave = note[:-1]+str(int(note[-1])-1)
                double = pitched(self.trumpet, 250.873629, octave, min(.45, gate))
                self.add('low-brass', 'trumpeten', beat+.015, double,
                         .18 if self.style in ('playful', 'bouncy') else .24, .25, octave)

    def groove_harmony(self):
        soft = self.style == 'lullaby'
        dance = self.style in ('dance', 'trance')
        rock = self.style in ('pop-rock', 'heavy-rock')
        for chord in self.score['chords']:
            start, length, notes = chord['beat'], chord['duration'], chord['notes']
            step = 2 if soft else (.5 if dance or self.style == 'pop-rock' else 1)
            for index, offset in enumerate(np.arange(0, length, step)):
                note = notes[-1] if (index % 4 == 2 or self.style == 'country' and index % 2) else notes[0]
                while legacy.frequency(note, 0) > 125:
                    note = note[:-1]+str(int(note[-1])-1)
                while legacy.frequency(note, 0) < 42:
                    note = note[:-1]+str(int(note[-1])+1)
                gate = min(.45 if soft else .27, (length-offset)*self.spb*.75)
                audio = pitched(self.bass, 80.769, note, gate)
                # Leave headroom for the low register in Shark/Sommartider.
                self.add('bass', 'smygaren', start+float(offset), audio,
                         .27 if soft else (.39 if dance else .42), 0, note)
            if soft:
                chord_offsets = np.arange(0, length, 4)
            elif self.style == 'country':
                chord_offsets = np.arange(.5, length, 1)
            elif dance:
                chord_offsets = np.arange(.5, length, 1)
            else:
                chord_offsets = np.arange(1, length, 2)
            for offset in chord_offsets:
                for voice, written in enumerate(notes[:3]):
                    note = written
                    while legacy.frequency(note, 0) < 145:
                        note = note[:-1]+str(int(note[-1])+1)
                    audio = pitched(self.duck, 82.276, note, .22 if soft else .14)
                    self.add('chords', 'ankan', start+float(offset), audio,
                             .12 if soft else (.23 if rock else .19), [-.4, .35, .1][voice], note)

    def groove_rhythm(self):
        soft = self.style == 'lullaby'
        dance = self.style in ('dance', 'trance')
        for beat in range(int(np.ceil(self.beats))):
            if beat >= self.beats: continue
            if soft:
                if beat % 4 == 0:
                    self.add('soft-pulse', 'kanonen', beat, natural_hit(self.bank, 'kanonen', .14, rate=.8), .15, -.12)
                if beat % 2 == 1:
                    self.add('brush', 'blota', beat, natural_hit(self.bank, 'blota', .10, bright=True), .10, .25)
            elif dance:
                self.add('kick', 'kanonen', beat, natural_hit(self.bank, 'kanonen', .13, rate=.75), .32, -.08)
                if beat % 2:
                    self.add('backbeat', 'blota', beat, natural_hit(self.bank, 'blota', .11, rate=1.25, bright=True), .26, .15)
                self.add('offbeat', 'snabbisen', beat+.5, natural_hit(self.bank, 'snabbisen', .038, rate=1.7, offset=.13, bright=True), .11, .32)
            elif self.style == 'heavy-rock':
                # Original melody uses half-time 68 BPM; the band drives at 136.
                for offset in (0, .5):
                    source = 'kanonen' if offset == 0 else 'blota'
                    self.add('heavy-beat', source, beat+offset,
                             natural_hit(self.bank, source, .17, rate=.8 if offset == 0 else 1.2), .35 if offset == 0 else .24, -.1 if offset == 0 else .16)
            elif self.style == 'country':
                self.add('boom', 'kanonen', beat, natural_hit(self.bank, 'kanonen', .11, rate=.85), .28, -.13)
                self.add('chick', 'snabbisen', beat+.5, natural_hit(self.bank, 'snabbisen', .07, rate=1.35, offset=.1, bright=True), .20, .25)
                if beat % 2:
                    self.add('wet-clap', 'blota', beat, natural_hit(self.bank, 'blota', .09, rate=1.3), .15, -.25)
            else:
                source = 'kanonen' if beat % 2 == 0 else 'blota'
                self.add('beat', source, beat, natural_hit(self.bank, source, .13, rate=.8 if beat % 2 == 0 else 1.2), .30 if self.style == 'pop-rock' else .21, -.1 if beat % 2 == 0 else .2)
            # Small recorded ticks mark space; avoid cluttering Sandstorm's pulse.
            if not soft and self.style != 'trance':
                for offset in ((.25, .75) if self.style == 'heavy-rock' else (0, .5)):
                    if beat+offset < self.beats:
                        self.add('ticks', 'snabbisen', beat+offset, natural_hit(self.bank, 'snabbisen', .025, rate=1.8, offset=.14, bright=True), .045 if dance else .055, -.3 if offset else .3)
        self.groove_fills()

    def groove_fills(self):
        soft = self.style == 'lullaby'
        dry = self.style == 'trance'
        # Quiet replies sit in actual melody rests where possible. Otherwise
        # phrase-end fills stay below the tune and retain the accepted pulse.
        for phrase in range(8, int(self.beats)+1, 8):
            offsets = (-.5, -.25) if dry or soft else (-.75, -.5, -.25)
            for index, offset in enumerate(offsets):
                source = ('ankan', 'snabbisen', 'blota')[index]
                self.add('fills', source, phrase+offset,
                         natural_hit(self.bank, source, .055 if dry else .085, rate=1.15+index*.15),
                         .07 if soft else (.12 if dry else .19), -.3+index*.3)
            if phrase < self.beats and phrase % 16 == 0:
                self.add('riser', 'raketen', phrase-.4/self.spb,
                         natural_hit(self.bank, 'raketen', .22, rate=1.25, reverse=True), .06 if soft else .11, .4)
        # Natural breathing gaps get an occasional duck-like reply, not a
        # competing melody. Only existing rests longer than .5 beats qualify.
        melody = self.score['melody']
        for previous, following in zip(melody, melody[1:]):
            end = previous['beat']+previous['duration']
            gap = following['beat']-end
            if gap >= .5:
                self.add('reply', 'ankan', end+min(.15, gap/4), natural_hit(self.bank, 'ankan', min(.18, gap*self.spb*.5), rate=1.1), .07 if soft else .14, -.3)

    def comedy(self):
        # A different low recorded growl marks the midpoint, and a theatrical
        # fart flourish resolves the final cadence. No new musical quote here.
        middle = min(self.beats-4, int(self.beats/8)*4)
        gentle = self.style == 'lullaby'
        tight = self.style == 'trance'
        self.add('growl', 'vulkanen', middle, natural_hit(self.bank, 'vulkanen', .25 if tight else .42, rate=.78, offset=.8), .06 if gentle else (.12 if tight else .23), -.35)
        end = self.beats-.5
        self.add('finale', 'katastrofen', end, natural_hit(self.bank, 'katastrofen', .7, rate=.88), .12 if gentle else .38, 0)
        self.add('finale', 'raketen', end+.25, natural_hit(self.bank, 'raketen', .4, rate=1.3, offset=.18), .05 if gentle else .12, .4)

    def mix(self):
        self.lead(); self.harmonic_backing(); self.rhythm(); self.comedy()
        dry = sum(self.stems.values())
        # A small recorded-signal echo adds space without smearing the next note.
        room = np.zeros_like(dry)
        for delay, level in ((.071, .065), (.119, .04)):
            n = round(delay*SR)
            room[n:] += dry[:-n, ::-1]*level
        mix = dry+room
        # Smooth, moderate bus saturation contains coincident fart transients.
        mix = np.tanh(mix*1.12)
        scale = .80/np.max(np.abs(mix))
        mix *= scale
        mix[-round(.2*SR):] *= np.linspace(1, 0, round(.2*SR))[:, None]
        return mix, scale


def validate(ffmpeg, path, orchestra, scale):
    raw = ffmpeg_run(ffmpeg, ['-i', str(path), '-f', 'f32le', '-ar', str(SR), '-ac', '2', 'pipe:1'])
    audio = np.frombuffer(raw, dtype='<f4').reshape(-1, 2).astype(float)
    peak = float(np.max(np.abs(audio)))
    assert 15 < len(audio)/SR < 45
    assert .15 < peak < .98 and not np.any(np.abs(audio) >= 1)
    lead = orchestra.stems['lead']*scale
    attacks = []
    for event in orchestra.events:
        if event['role'] != 'lead': continue
        start = round(event['start_seconds']*SR)
        span = min(round(.08*SR), round(event['length_seconds']*SR))
        attacks.append(float(np.sqrt(np.mean(lead[start:start+span]**2))))
    assert min(attacks) > .008, 'Lead must be audible before mixing'
    rms = {key: float(np.sqrt(np.mean(value**2)))*scale for key, value in orchestra.stems.items()}
    assert rms['lead'] > max(v for k, v in rms.items() if k != 'lead'), 'Lead must be the strongest single stem'
    used = sorted(set(event['source'] for event in orchestra.events))
    assert len(used) >= 8, 'Orchestra should use many different real fart recordings'
    return dict(duration_seconds=round(len(audio)/SR, 4), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(), peak=round(peak, 6),
                rms=round(float(np.sqrt(np.mean(audio**2))), 6), clipping_samples=0,
                audible_recorded_attacks=len(attacks), minimum_attack_rms=round(min(attacks), 6),
                recorded_source_count=len(used), sources_used=used,
                layer_rms={key: round(value, 6) for key, value in rms.items()},
                event_count=len(orchestra.events), channels=2, bitrate_kbps=128)


def main():
    scores = json.loads((ROOT/'tools/orchestra-scores.json').read_text(encoding='utf-8'))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    parser.add_argument('--only', nargs='+', choices=[score['id'] for score in scores])
    args = parser.parse_args()
    bank, sources = load_sources(args.ffmpeg)
    metadata_path = ROOT/'audio/songs/metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    # The user approved Imperial March's audio. Keep that delivered file and
    # metadata untouched unless it is explicitly selected for regeneration.
    targets = args.only or [s['id'] for s in scores if s['id'] != 'imperial-march']
    for previous in metadata['songs']:
        if previous['id'] not in targets:
            assert hashlib.sha256((ROOT/previous['file']).read_bytes()).hexdigest() == previous['validation']['sha256'], 'Existing song changed'
    additions = {}
    for score in scores:
        if score['id'] not in targets: continue
        orchestra = Orchestra(score, bank, args.ffmpeg)
        audio, scale = orchestra.mix()
        path = ROOT/'audio/songs'/f"{score['id']}.mp3"
        ffmpeg_run(args.ffmpeg, ['-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', 'pipe:0',
            '-c:a', 'libmp3lame', '-b:a', '128k', '-id3v2_version', '3',
            '-metadata', 'title='+score['title'], '-metadata', 'artist=Fart Machine',
            '-metadata', 'comment=Layered fart orchestra made from nine credited CC0 recordings',
            str(path)], audio.astype('<f4').tobytes())
        report = validate(args.ffmpeg, path, orchestra, scale)
        additions[score['id']] = dict(id=score['id'], title=score['title'], bpm=score['bpm'],
            meter=score['meter'], melody=score['title']+' — '+score['composer'],
            composition_rights='Copyrighted composition; CC0 applies only to the source fart recordings',
            file='audio/songs/'+path.name,
            arrangement=('Arena-rock fart fanfare with sustained recorded-fart lead, octave brass, galloping bass, chord replies, wet rock backbeat, short puffs, phrase fills and comic finale' if score['id'] == 'the-final-countdown' else score.get('style', 'march')+' fart orchestra with tuned lead, bass, chord replies, a distinct rhythmic groove, short recorded attacks, phrase fills and a comic ending'),
            source_notation=score['source_notes'], references=score['references'],
            format=dict(codec='mp3', mime='audio/mpeg', sample_rate=SR, channels=2, bitrate_kbps=128),
            notes=score['melody'], chords=score['chords'],
            orchestra=dict(sources=[s for s in sources if s['key'] in report['sources_used']],
                           events=orchestra.events, no_oscillators=True, no_original_song_audio=True),
            validation=report)
        if 'key_change_from_previous_semitones' in score:
            additions[score['id']]['key_change_from_previous_semitones'] = score['key_change_from_previous_semitones']
        print(json.dumps({'id': score['id'], **report}, ensure_ascii=False), flush=True)
    # Retain metadata entries in their existing order; append new songs in score order.
    metadata['songs'] = [additions.pop(s['id'], s) for s in metadata['songs']]
    metadata['songs'].extend(additions.values())
    metadata['orchestra_format'] = dict(codec='mp3', mime='audio/mpeg', sample_rate=SR, channels=2, bitrate_kbps=128)
    metadata['format'] = metadata['orchestra_format'].copy()
    metadata['articulation'] = 'Ten layered recorded-fart orchestras with distinct grooves; Sandstorm retains its tight alternating attacks; all sources, musical roles and timing are documented per song'
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__': main()
