"""Import only the selected CC0 Freesound recordings; never execute downloaded data."""
import hashlib
import html
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SOUNDS = [
    ('smygaren', 'Smygaren', 'Breviceps', 445998, 9159316, 'Fart 1'),
    ('kanonen', 'Kanonen', 'Breviceps', 445999, 9159316, 'Fart 2'),
    ('blota', 'Blota', 'Breviceps', 445997, 9159316, 'Diarrhea'),
    ('trumpeten', 'Trumpeten', 'sorce', 431621, 144433, 'fart,bum,trumpet,poop.wav'),
    ('ankan', 'Ankan', 'Breviceps', 446000, 9159316, 'Fart 3'),
    ('vulkanen', 'Vulkanen', 'Blubberfreak', 732057, None, 'Blubberfreak Fart 3'),
    ('snabbisen', 'Snabbisen', 'C-V', 506994, None, 'FART.wav'),
    ('raketen', 'Raketen', 'SamuelGremaud', 518699, 8031303, 'FART - 2'),
    ('katastrofen', 'Katastrofen', 'Under7dude', 163381, None, 'Fart 3'),
]
OUT = Path('audio')
OUT.mkdir(exist_ok=True)
ALLOWED = {'freesound.org', 'www.freesound.org', 'cdn.freesound.org'}


def download(url, limit=2_000_000):
    from urllib.parse import urlparse
    if urlparse(url).scheme != 'https' or urlparse(url).hostname not in ALLOWED:
        raise ValueError('Unapproved download host')
    request = urllib.request.Request(url, headers={'User-Agent': 'Pruttmaskin-CC0-audio-import/3.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        if urlparse(response.url).hostname not in ALLOWED:
            raise ValueError('Unapproved redirect host')
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Download exceeds size limit')
        return data


records, errors = [], []
for key, label, author, sid, uid, title in SOUNDS:
    page = f'https://freesound.org/people/{author}/sounds/{sid}/'
    try:
        candidates = []
        if uid:
            candidates.append(f'https://cdn.freesound.org/previews/{sid // 1000}/{sid}_{uid}-hq.mp3')
        if not uid:
            text = html.unescape(download(page).decode('utf-8')).replace('\\/', '/')
            if 'creativecommons.org/publicdomain/zero/1.0' not in text:
                raise ValueError('Expected CC0 license not found on source page')
            paths = re.findall(r'/previews/\d+/' + str(sid) + r'_\d+-hq\.mp3', text)
            candidates.extend('https://cdn.freesound.org' + path for path in dict.fromkeys(paths))
        if not candidates:
            raise ValueError('Public high-quality preview URL missing')
        source = candidates[0]
        data = download(source)
        target = OUT / (key + '.mp3')
        target.write_bytes(data)
        probe = subprocess.check_output([
            'ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
            'stream=codec_name,sample_rate,channels:format=duration', '-of', 'json', str(target)
        ], text=True)
        info = json.loads(probe)
        duration = float(info['format']['duration'])
        if not info.get('streams') or info['streams'][0]['codec_name'] != 'mp3' or not (0.1 < duration < 12):
            target.unlink(missing_ok=True)
            raise ValueError('Unexpected audio format or duration')
        records.append({'key': key, 'file': str(target), 'title': title, 'author': author,
                        'source_page': page, 'download_url': source, 'license': 'CC0-1.0',
                        'license_url': 'https://creativecommons.org/publicdomain/zero/1.0/',
                        'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                        'duration': duration, 'format': info['streams'][0]})
        print(key, len(data), round(duration, 3), 'seconds', flush=True)
    except Exception as exc:
        errors.append({'key': key, 'source_page': page, 'error': str(exc)})
        print(key, 'FAILED:', str(exc), flush=True)
    time.sleep(0.5)

(OUT / 'sources.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
(OUT / 'import-report.json').write_text(json.dumps({'ok': len(records) == 9, 'count': len(records), 'errors': errors}, indent=2) + '\n')
credits = ['# Recorded sound credits', '', 'All nine selected recordings are released by their authors under CC0 1.0.',
           'License: https://creativecommons.org/publicdomain/zero/1.0/', '',
           'Files are copies of the publicly playable high-quality MP3 previews. No synthetic sound generation is used.', '',
           'Sources and SHA-256 checksums are recorded in sources.json.', '']
for r in records:
    credits += [f"- **{r['key']}**: {r['title']} by {r['author']}", f"  {r['source_page']}"]
(OUT / 'CREDITS.md').write_text('\n'.join(credits) + '\n')
if errors:
    sys.exit(1)
