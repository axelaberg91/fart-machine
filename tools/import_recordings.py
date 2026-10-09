"""Import selected CC0 recordings without installing any system packages."""
import hashlib
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

SOUNDS = [
    ('smygaren', 'Breviceps', 445998, 9159316, 'Fart 1'),
    ('kanonen', 'Breviceps', 445999, 9159316, 'Fart 2'),
    ('blota', 'Breviceps', 445997, 9159316, 'Diarrhea'),
    ('trumpeten', 'sorce', 431621, 144433, 'fart,bum,trumpet,poop.wav'),
    ('ankan', 'Breviceps', 446000, 9159316, 'Fart 3'),
    ('vulkanen', 'Blubberfreak', 732057, None, 'Blubberfreak Fart 3'),
    ('snabbisen', 'C-V', 506994, None, 'FART.wav'),
    ('raketen', 'SamuelGremaud', 518699, 8031303, 'FART - 2'),
    ('katastrofen', 'Under7dude', 163381, None, 'Fart 3'),
]
OUT = Path('audio')
OUT.mkdir(exist_ok=True)
ALLOWED = {'freesound.org', 'www.freesound.org', 'cdn.freesound.org'}

def download(url, limit=2_000_000):
    if urlparse(url).scheme != 'https' or urlparse(url).hostname not in ALLOWED:
        raise ValueError('Unapproved download host')
    request = urllib.request.Request(url, headers={'User-Agent': 'Pruttmaskin-CC0-audio-import/3.0'})
    with urllib.request.urlopen(request, timeout=25) as response:
        if urlparse(response.url).hostname not in ALLOWED:
            raise ValueError('Unapproved redirect host')
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Download exceeds size limit')
        return data

def probe_mp3(data):
    """Check MPEG Layer III frames; this is structural validation, not an audio audition."""
    pos, frames, duration, first = 0, 0, 0.0, None
    if data[:3] == b'ID3' and len(data) >= 10:
        pos = 10 + sum((data[6 + i] & 127) << (7 * (3 - i)) for i in range(4))
    while pos + 4 < len(data):
        h = int.from_bytes(data[pos:pos + 4], 'big')
        version, layer, bi, si = (h >> 19) & 3, (h >> 17) & 3, (h >> 12) & 15, (h >> 10) & 3
        if h >> 21 != 2047 or version == 1 or layer != 1 or bi in (0, 15) or si == 3:
            pos += 1
            continue
        table = [0,32,40,48,56,64,80,96,112,128,160,192,224,256,320] if version == 3 else [0,8,16,24,32,40,48,56,64,80,96,112,128,144,160]
        rate = [44100,48000,32000][si] // (1 if version == 3 else 2 if version == 2 else 4)
        length = (144 if version == 3 else 72) * table[bi] * 1000 // rate + ((h >> 9) & 1)
        if pos + length > len(data):
            break
        first = first or {'codec_name':'mp3','sample_rate':str(rate),'channels':1 if (h >> 6) & 3 == 3 else 2,'validator':'MPEG Layer III frame scan'}
        frames += 1
        duration += (1152 if version == 3 else 576) / rate
        pos += length
    if frames < 3 or not (0.1 < duration < 12):
        raise ValueError('Invalid MP3 frames or unexpected duration')
    return duration, first

records, errors = [], []
for key, author, sid, uid, title in SOUNDS:
    page = f'https://freesound.org/people/{author}/sounds/{sid}/'
    try:
        if uid:
            source = f'https://cdn.freesound.org/previews/{sid // 1000}/{sid}_{uid}-hq.mp3'
        else:
            text = html.unescape(download(page).decode('utf-8')).replace('\\/', '/')
            if 'creativecommons.org/publicdomain/zero/1.0' not in text:
                raise ValueError('Expected CC0 license missing on source page')
            paths = re.findall(r'/previews/\d+/' + str(sid) + r'_\d+-hq\.mp3', text)
            if not paths:
                raise ValueError('Public high-quality MP3 URL missing')
            source = 'https://cdn.freesound.org' + paths[0]
        data = download(source)
        duration, info = probe_mp3(data)
        digest = hashlib.sha256(data).hexdigest()
        if any(r['sha256'] == digest for r in records):
            raise ValueError('Duplicate recording')
        target = OUT / (key + '.mp3')
        target.write_bytes(data)
        records.append({'key':key,'file':str(target),'title':title,'author':author,'source_page':page,
                        'download_url':source,'license':'CC0-1.0','license_url':'https://creativecommons.org/publicdomain/zero/1.0/',
                        'sha256':digest,'bytes':len(data),'duration':round(duration,6),'format':info})
        print(key,len(data),round(duration,3),'seconds',flush=True)
    except Exception as exc:
        errors.append({'key':key,'source_page':page,'error':str(exc)})
        print(key,'FAILED:',str(exc),flush=True)
    time.sleep(0.3)

(OUT/'sources.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
(OUT/'import-report.json').write_text(json.dumps({'ok':len(records)==9,'count':len(records),'errors':errors},indent=2)+'\n')
credits = ['# Recorded sound credits','','The successfully imported recordings below are CC0 1.0.',
           'License: https://creativecommons.org/publicdomain/zero/1.0/','',
           'Unmodified copies of the publicly playable high-quality MP3 previews. No synthesis.',
           'See sources.json for source URLs, authors, sizes and SHA-256 checksums.','']
for r in records:
    credits += [f"- **{r['key']}**: {r['title']} by {r['author']}",f"  {r['source_page']}"]
(OUT/'CREDITS.md').write_text('\n'.join(credits)+'\n')
if errors:
    sys.exit(1)
