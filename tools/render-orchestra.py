#!/usr/bin/env python3
"""Render two layered fart orchestras; retain every existing song byte-for-byte.

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
        self.spb = 60/score['bpm']
        self.beats = score.get('total_beats', score['bars']*4)
        self.length = round((self.beats*self.spb+1.2)*SR)
        self.stems = {}
        self.events = []
        self.ffmpeg = ffmpeg
        self.long_notes = {}
        self.trumpet = normalized(crop(bank, 'trumpeten', 1.49, .45), .23)
        self.bass = normalized(crop(bank, 'smygaren', .20, .46), .22)
        self.duck = normalized(crop(bank, 'ankan', .08, .27), .17)

    def sustained_lead(self, note, duration):
        key = (note, round(duration, 5))
        if key not in self.long_notes:
            hz = legacy.frequency(note, 0)
            natural_duration = len(self.trumpet)/SR*250.873629/hz
            raw = pitched(self.trumpet, 250.873629, note, natural_duration)
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

    def comedy(self):
        # A different low recorded growl marks the midpoint, and a theatrical
        # fart flourish resolves the final cadence. No new musical quote here.
        middle = min(self.beats-4, int(self.beats/8)*4)
        self.add('growl', 'vulkanen', middle, natural_hit(self.bank, 'vulkanen', .42, rate=.78, offset=.8), .23, -.35)
        end = self.beats-.5
        self.add('finale', 'katastrofen', end, natural_hit(self.bank, 'katastrofen', .7, rate=.88), .38, 0)
        self.add('finale', 'raketen', end+.25, natural_hit(self.bank, 'raketen', .4, rate=1.3, offset=.18), .12, .4)

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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    parser.add_argument('--only', nargs='+', choices=['the-final-countdown', 'imperial-march'])
    args = parser.parse_args()
    scores = json.loads((ROOT/'tools/orchestra-scores.json').read_text(encoding='utf-8'))
    bank, sources = load_sources(args.ffmpeg)
    metadata_path = ROOT/'audio/songs/metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    targets = args.only or [s['id'] for s in scores]
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
            arrangement=('Arena-rock fart fanfare with sustained recorded-fart lead, octave brass, galloping bass, chord replies, wet rock backbeat, short puffs, phrase fills and comic finale' if score['id'] == 'the-final-countdown' else 'Marching fart brass band with sustained recorded-fart lead, octave brass, heavy bass steps, chord replies, alternating side rolls, phrase fills and comic finale'),
            source_notation=score['source_notes'], references=score['references'],
            format=dict(codec='mp3', mime='audio/mpeg', sample_rate=SR, channels=2, bitrate_kbps=128),
            notes=score['melody'], chords=score['chords'],
            orchestra=dict(sources=[s for s in sources if s['key'] in report['sources_used']],
                           events=orchestra.events, no_oscillators=True, no_original_song_audio=True),
            validation=report)
        print(json.dumps({'id': score['id'], **report}, ensure_ascii=False), flush=True)
    # Retain metadata entries in their existing order; append new songs in score order.
    metadata['songs'] = [additions.pop(s['id'], s) for s in metadata['songs']]
    metadata['songs'].extend(additions.values())
    metadata['orchestra_format'] = dict(codec='mp3', mime='audio/mpeg', sample_rate=SR, channels=2, bitrate_kbps=128)
    metadata['articulation'] = 'Eight solo renditions retain their previous recorded-fart articulation; two layered orchestras use the sources, processing and event roles documented per song'
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__': main()
