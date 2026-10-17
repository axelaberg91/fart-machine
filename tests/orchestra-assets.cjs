'use strict';

// Integration contract for the two approved richer arrangements. Examines the
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

for (const id of ['the-final-countdown', 'imperial-march']) {
  const song = metadata.songs.find(entry => entry.id === id);
  assert.ok(song, id + ' published in song metadata');
  assert.deepEqual(song.format, { codec: 'mp3', mime: 'audio/mpeg', sample_rate: 44100, channels: 2, bitrate_kbps: 128 });
  const output = fs.readFileSync(path.join(root, song.file));
  assert.equal(output.length, song.validation.bytes, id + ' output byte count');
  assert.equal(hash(output), song.validation.sha256, id + ' output hash');
  const actualDuration = inspectMp3(output, id);
  assert.ok(actualDuration > 15 && actualDuration < 45, id + ' output lasts 15–45 seconds');
  assert.ok(Math.abs(actualDuration - song.validation.duration_seconds) < 0.12, id + ' MP3 frame duration matches decoded validation');
  assert.equal(song.validation.clipping_samples, 0, id + ' decoded validation reports no clipping');
  assert.ok(song.validation.peak > 0.15 && song.validation.peak < 0.98, id + ' decoded peak leaves headroom');
  assert.equal(song.orchestra.no_original_song_audio, true, id + ' uses independently arranged material');
  assert.equal(song.orchestra.no_oscillators, true, id + ' uses recorded fart sounds');

  const sources = song.orchestra.sources;
  assert.ok(sources.length >= 8, id + ' credits at least eight distinct recorded sources');
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
