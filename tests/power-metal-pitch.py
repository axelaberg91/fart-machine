#!/usr/bin/env python3
"""Check physical pitch centring and dry note gaps in the rapid recorded lead.

Run with Python/NumPy and FFmpeg:
python tests/power-metal-pitch.py --ffmpeg /path/to/ffmpeg
This measures audio; it does not copy the renderer's tuning calculation.
"""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ffmpeg',default='ffmpeg')
args=parser.parse_args()
spec=importlib.util.spec_from_file_location('orchestra',root/'tools/render-orchestra.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
score=next(s for s in json.loads((root/'tools/orchestra-scores.json').read_text(encoding='utf-8'))
           if s['id']=='through-the-fire-and-flames')
bank,_=renderer.load_sources(args.ffmpeg)
orchestra=renderer.Orchestra(score,bank,args.ffmpeg)
orchestra.lead()
lead=orchestra.stems['lead']
events=[e for e in orchestra.events if e['role']=='lead']
errors=[];gap_levels=[]
for event in events:
    target=renderer.legacy.frequency(event['note'],0)
    start=round((event['start_seconds']+.009)*renderer.SR)
    end=round((event['start_seconds']+min(event['length_seconds']-.007,.065))*renderer.SR)
    sample=lead[start:end].mean(axis=1)
    if len(sample)<round(renderer.SR/target*5): continue
    sample=(sample-sample.mean())*np.hanning(len(sample))
    spectrum=np.fft.rfft(sample,n=8192)
    correlation=np.fft.irfft(spectrum*spectrum.conj())
    low=max(2,round(renderer.SR/target*.88))
    high=min(len(sample)//2,round(renderer.SR/target*1.12))
    if high<=low: continue
    lag=int(np.argmax(correlation[low:high+1]))+low
    if lag in (low,high): continue
    left,centre,right=correlation[lag-1:lag+2]
    fraction=.5*(left-right)/(left-2*centre+right)
    measured=renderer.SR/(lag+fraction)
    errors.append(float(1200*np.log2(measured/target)))
for previous,following in zip(events,events[1:]):
    end=previous['start_seconds']+previous['length_seconds']
    start=following['start_seconds']
    if start-end>=.006:
        gap=lead[round((end+.001)*renderer.SR):round((start-.001)*renderer.SR)]
        if len(gap):gap_levels.append(float(np.sqrt(np.mean(gap*gap))))
assert len(events)==len(score['melody']) and len(errors)>.9*len(events)
assert np.median(np.abs(errors))<40,'Rapid lead drifts too far from the written pitches'
assert np.percentile(np.abs(errors),95)<65,'Too many rapid notes have substantial pitch drift'
assert len(gap_levels)>.9*(len(events)-1),'Rapid line needs separate articulated attacks'
assert max(gap_levels)<.0001,'The dry lead smears across following note attacks'
print(f'PASS power-metal lead: {len(events)} notes, median pitch error '
      f'{np.median(np.abs(errors)):.2f} cents, '
      f'{len(gap_levels)} silent dry gaps, {score["bpm"]} BPM.')
