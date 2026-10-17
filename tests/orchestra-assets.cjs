'use strict';

// Integration contract for all twelve layered arrangements. Examines the
// shipped assets and their provenance, without importing the audio renderer.
// Run with: node tests/orchestra-assets.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const root = path.resolve(__dirname, '..');
const metadata = JSON.parse(fs.readFileSync(path.join(root, 'audio/songs/metadata.json'), 'utf8'));
const sourceManifest = JSON.parse(fs.readFileSync(path.join(root, 'audio/sources.json'), 'utf8'));
const manifestByKey = new Map(sourceManifest.map(source => [source.key, source]));
const hash = data => createHash('sha256').update(data).digest('hex');
const retainedSongHashes = {
  "greta-gris": "ae5d0eea697f5e9ac360da8cfe46beb1805c06efb3cf827551482452010a6716",
  "bjornen-sover": "71ddd2a61bfaa4c7540985e36df5af0ac54520b05c0beb32349f381243386ccc",
  "baby-shark": "6bd468de64856a28d610a8bef73c537cb8926ee729fd3cf55262ffb75a6682bc",
  "en-livstid-i-krig": "cdddfe5f63255f73887758fa299270b5cedb3f40b110aa7669d5876d432516bf",
  "bromance": "277366c4558deb513a478eb0938eb7b354ea340ed592a470b18513f55fcf58e7",
  "sommartider": "cd0c91f74958deadc002f22d4e6e1dbd86c05668d8112a1c5db874f61f75cf17",
  "sandstorm": "2bc5a4a0fc2bf40cc7acfd6dce1f93ed9c0427524d130fb90182c993806a82fb",
  "ring-of-fire": "41d4a459c0ee0c53ed79cdbe720ff410e275d8b3018ac8393b3c819f14f0d3e6",
  "the-final-countdown": "3fdc6d8e18d516dfcdbada426efdb08118081e88c9a63bf47f1e2af5de773f84",
  "imperial-march": "2bf7cad4826c8d9b18e808f909ea1b4a0d7e1d6b5b4d4336afbb062b1fbb2942",
  "seven-nation-army": "d7390e70fc9d245cef2f04bd2f60b11f16fcd80b29a88334ff689bdb746dee44",
  "through-the-fire-and-flames": "19f136ad5f55500090ef245621135b0ec9589bdb56e0df6332b16a21065cc314"
};
const retainedMetadataHashes = {
  "greta-gris": "ee4430edc593842c2089dd7a8eed9e1c0cac5f83621ebf104aebeda1a8872877",
  "bjornen-sover": "c199821a8c83e47aaa9443c5eb4c564c4aa42bcd3ac226cf718c29b2c3d62674",
  "baby-shark": "1b5e5906094e0f6d47fae9425b3ddb24e5f75f8e57c63fc73cec7117a91c9547",
  "en-livstid-i-krig": "c4573378e8bba60b556c2a51500a4e7fbf47cd0d1ccacb0721993faf633e343c",
  "bromance": "dff457348c41b3fafa01877ff1ed16dbddf4da72efd2dfcfdaeb5a43e7b9f7aa",
  "sommartider": "3842b16ed185db560616fa101407d240ca488b21e70e70166ede7295ba65ce30",
  "sandstorm": "9b801ffe51c1e37455f3fa73eccf149f822a688d3539bc8dc99763123906ddbc",
  "ring-of-fire": "40a7c51b58a8379b3066fbceb89c54793c37275c8675973d927a01a6ceb44348",
  "the-final-countdown": "2ef1e2df85e624cd9ce59c37502da349a0e0e5d63bd9a9e496e4a03262bb4ad0",
  "imperial-march": "46aede4e9d1f3b3db3dffcd0064c41d63d54c42c2402735ea2fef0c51770af86",
  "seven-nation-army": "fdbf594b3eba334c7346ce4a30fad63808057541d2395420b859211e0859914f",
  "through-the-fire-and-flames": "dca9e35e11c55197a387d815fdbdfab3b7d6db3671b5a530e8996858b6ed3f0d"
};
const expectedIds = ['greta-gris', 'bjornen-sover', 'baby-shark', 'en-livstid-i-krig', 'bromance', 'sommartider', 'sandstorm', 'ring-of-fire', 'the-final-countdown', 'imperial-march', 'seven-nation-army', 'through-the-fire-and-flames'];
assert.deepEqual(metadata.songs.map(song => song.id), expectedIds, 'all twelve arrangements stay in the approved order');

function maximumSimultaneousRoles(events) {
  const edges = events.flatMap(event => [
    { time: event.start_seconds, change: 1, role: event.role },
    { time: event.start_seconds + event.length_seconds, change: -1, role: event.role }
  ]).sort((a, b) => a.time - b.time || a.change - b.change);
  const active = new Map();
  let maximum = 0;
  for (const edge of edges) {
    const count = (active.get(edge.role) || 0) + edge.change;
    if (count) active.set(edge.role, count);
    else active.delete(edge.role);
    maximum = Math.max(maximum, active.size);
  }
  return maximum;
}

function inspectMp3(data, id) {
  let offset = 0;
  if (data.toString('ascii', 0, 3) === 'ID3') {
    assert.ok(data.subarray(6, 10).every(byte => byte < 128), id + ' valid ID3 size');
    offset = 10 + data.subarray(6, 10).reduce((size, byte) => size * 128 + byte, 0);
    if (data[5] & 16) offset += 10;
  }
  let frames = 0;
  while (offset + 4 <= data.length) {
    if (data.toString('ascii', offset, offset + 3) === 'TAG' && offset + 128 === data.length) { offset += 128; break; }
    const header = data.readUInt32BE(offset);
    assert.equal(header >>> 21, 0x7ff, id + ' consecutive valid MPEG frames');
    assert.equal((header >>> 19) & 3, 3, id + ' MPEG-1');
    assert.equal((header >>> 17) & 3, 1, id + ' Layer III');
    const bitrate = [0,32,40,48,56,64,80,96,112,128,160,192,224,256,320][(header >>> 12) & 15];
    const sampleRate = [44100,48000,32000][(header >>> 10) & 3];
    assert.equal(bitrate, 128, id + ' actual 128 kbps MP3');
    assert.equal(sampleRate, 44100, id + ' actual 44.1 kHz MP3');
    assert.notEqual((header >>> 6) & 3, 3, id + ' actual stereo MP3');
    offset += Math.floor(144000 * bitrate / sampleRate) + ((header >>> 9) & 1);
    assert.ok(offset <= data.length, id + ' no truncated MPEG frames');
    frames++;
  }
  assert.ok(frames > 100, id + ' contains a complete musical excerpt');
  assert.equal(offset, data.length, id + ' all MP3 bytes belong to complete frames');
  return frames * 1152 / 44100;
}

for (const id of expectedIds) {
  const song = metadata.songs.find(entry => entry.id === id);
  assert.ok(song, id + ' published in song metadata');
  assert.deepEqual(song.format, { codec: 'mp3', mime: 'audio/mpeg', sample_rate: 44100, channels: 2, bitrate_kbps: 128 });
  const output = fs.readFileSync(path.join(root, song.file));
  assert.equal(output.length, song.validation.bytes, id + ' output byte count');
  assert.equal(hash(output), song.validation.sha256, id + ' output hash');
  if (retainedSongHashes[id]) {
    assert.equal(hash(output), retainedSongHashes[id], id + ' approved recording stays byte-for-byte unchanged');
    assert.equal(hash(JSON.stringify(song)), retainedMetadataHashes[id], id + ' approved metadata stays unchanged');
  }
  const actualDuration = inspectMp3(output, id);
  assert.ok(actualDuration > 15 && actualDuration < 45, id + ' output lasts 15–45 seconds');
  assert.ok(Math.abs(actualDuration - song.validation.duration_seconds) < 0.12, id + ' MP3 frame duration matches decoded validation');
  assert.equal(song.validation.clipping_samples, 0, id + ' decoded validation reports no clipping');
  assert.ok(song.validation.peak > 0.15 && song.validation.peak < 0.98, id + ' decoded peak leaves headroom');
  assert.equal(song.orchestra.no_original_song_audio, true, id + ' uses independently arranged material');
  assert.equal(song.orchestra.no_oscillators, true, id + ' uses recorded fart sounds');

  const sources = song.orchestra.sources;
  assert.equal(sources.length, 9, id + ' credits all nine distinct recorded sources');
  assert.equal(new Set(sources.map(source => source.key)).size, sources.length, id + ' unique source keys');
  assert.equal(new Set(sources.map(source => source.sha256)).size, sources.length, id + ' sources contain distinct recordings');
  for (const source of sources) {
    const manifest = manifestByKey.get(source.key);
    assert.ok(manifest, id + ' source exists in canonical manifest: ' + source.key);
    assert.equal(source.license, 'CC0-1.0', id + ' source has CC0 license: ' + source.key);
    for (const field of ['file', 'sha256', 'source_page', 'author', 'license']) assert.equal(source[field], manifest[field], id + ' attribution matches source manifest: ' + source.key + '.' + field);
    const data = fs.readFileSync(path.join(root, source.file));
    assert.equal(data.length, manifest.bytes, source.key + ' source byte count');
    assert.equal(hash(data), manifest.sha256, source.key + ' source payload matches manifest');
  }

  const sourceKeys = new Set(sources.map(source => source.key));
  const events = song.orchestra.events;
  assert.ok(Array.isArray(events) && events.length > 0, id + ' has an arrangement event ledger');
  assert.deepEqual([...new Set(events.map(event => event.source))].sort(), [...sourceKeys].sort(), id + ' credits match the sources actually used');
  assert.equal(song.validation.event_count, events.length, id + ' validation covers every arrangement event');
  for (const event of events) {
    assert.ok(event.role && Number.isFinite(event.start_seconds) && event.start_seconds >= 0, id + ' valid layer timing');
    assert.ok(Number.isFinite(event.length_seconds) && event.length_seconds > 0, id + ' nonempty articulation');
    assert.ok(event.start_seconds + event.length_seconds <= song.validation.duration_seconds + 0.002, id + ' event stays within delivered audio');
    assert.ok(Number.isFinite(event.gain) && event.gain > 0, id + ' audible gain');
    assert.ok(Number.isFinite(event.pan) && Math.abs(event.pan) <= 1, id + ' valid stereo position');
  }
  const roles = Object.entries(song.validation.layer_rms).filter(([, level]) => Number.isFinite(level) && level > 0);
  assert.ok(roles.length >= 4, id + ' at least four non-silent musical roles');
  const simultaneousRoles = maximumSimultaneousRoles(events);
  assert.ok(simultaneousRoles >= 4, id + ' at least four musical roles sound together');
  assert.ok(roles.some(([role]) => role === 'lead') && roles.some(([role]) => role === 'bass'), id + ' carries lead and bass');
  console.log('PASS ' + id + ': ' + sources.length + ' CC0 recordings, ' + roles.length + ' audible roles, ' + simultaneousRoles + ' simultaneous roles; complete stereo 128 kbps MP3.');
}
