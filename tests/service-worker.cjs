'use strict';

// Pure checks for the offline asset manifest and HTTP byte ranges.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { createHash } = require('node:crypto');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const expectedSongIds = ['greta-gris', 'bjornen-sover', 'baby-shark', 'en-livstid-i-krig', 'bromance', 'sommartider', 'through-the-fire-and-flames'];
const retainedSongHashes = {
  'greta-gris': '773755c69f926f9422d5b6df44f32fec44045a1b8329ac9d77aa0417dc74fc37',
  'bjornen-sover': '7cf0cc79156bfa228a9ec0a089b4ea172396e867a6a83c6aa16b4546a26264b8',
  'baby-shark': 'f24b28f778462916fb52c62bd6dd88f3767e05433ba64400ab8a74fa6001b8f7',
  'en-livstid-i-krig': 'e0767b28d081eee8ed85713d97fcce3f4876d3dcac5f8f62df9b9f4c51274bca',
  'bromance': 'a522b3681e7c938fcd1feaf7dc80f47150e2c9295508f23bc32d3059b5455c8f',
  'sommartider': '432a10395f5112889ad50d41ea2d6cc83fbc816e0c0df855a556c8883a173ad0'
};
const code = fs.readFileSync(path.join(root, 'sw.js'), 'utf8');
const context = vm.createContext({ self: { addEventListener() {} }, URL, Request, Response });
new vm.Script(code, { filename: 'sw.js' }).runInContext(context);
const rangeResponse = vm.runInContext('audioRange', context);
const assets = Array.from(vm.runInContext('ASSETS', context));
const version = vm.runInContext('VERSION', context);
assert.equal(version, '4.7.0');
assert.ok(assets.includes('./app-v4.4.js'));
assert.deepEqual(assets.filter(asset => asset.startsWith('./audio/songs/')).sort(), expectedSongIds.map(id => './audio/songs/' + id + '.mp3').sort());
assert.equal(assets.filter(asset => /^\.\/audio\/[^/]+\.mp3$/.test(asset)).length, 9);
assert.equal(new Set(assets).size, assets.length);
assert.equal(assets.length, 31);
new vm.Script(fs.readFileSync(path.join(root, 'app-v4.4.js'), 'utf8'), { filename: 'app-v4.4.js' });
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
assert.match(html, /app-v4\.4\.js/);
assert.match(html, /Version 4\.7\.0/);

async function main() {
  const source = Uint8Array.from({ length: 256 }, (_, index) => index);
  const cases = [
    { request: 'bytes=0-63', start: 0, end: 63 },
    { request: 'bytes=100-', start: 100, end: 255 },
    { request: 'bytes=-32', start: 224, end: 255 },
    { request: 'bytes=240-999', start: 240, end: 255 },
    { request: 'bytes=-999', start: 0, end: 255 }
  ];
  for (const test of cases) {
    const response = await rangeResponse(new Response(source, { headers: { 'Content-Type': 'audio/mpeg' } }), test.request);
    assert.equal(response.status, 206, test.request);
    assert.equal(response.headers.get('Content-Type'), 'audio/mpeg');
    assert.equal(response.headers.get('Accept-Ranges'), 'bytes');
    assert.equal(response.headers.get('Content-Length'), String(test.end - test.start + 1));
    assert.equal(response.headers.get('Content-Range'), 'bytes ' + test.start + '-' + test.end + '/256');
    assert.deepEqual(new Uint8Array(await response.arrayBuffer()), source.slice(test.start, test.end + 1));
  }
  for (const request of ['bytes=256-', 'bytes=8-4', 'bytes=-0', 'bytes=9007199254740992-']) {
    const response = await rangeResponse(new Response(source), request);
    assert.equal(response.status, 416, request);
    assert.equal(response.headers.get('Content-Range'), 'bytes */256');
  }
  for (const request of ['bytes=-', 'something-invalid', 'bytes=0-1,3-4']) {
    const response = await rangeResponse(new Response(source), request);
    assert.equal(response.status, 200, request);
    assert.deepEqual(new Uint8Array(await response.arrayBuffer()), source);
  }
  const missing = assets.filter(asset => asset !== './' && !fs.existsSync(path.join(root, asset)));
  console.log('PASS app/service-worker syntax, version references, complete sixteen-recording manifest, byte ranges, suffix ranges, and invalid ranges.');
  if (missing.length) console.log('Manifest files still pending: ' + missing.join(', '));
  else console.log('PASS all manifest assets exist.');
  if (process.argv.includes('--require-assets')) assert.deepEqual(missing, [], 'every offline asset must be present');
  for (const id of ['spoket-laban', 'lover', 'paw-patrol', 'puerto-rico', 'ghosts-n-stuff', 'sommar-och-sol']) assert.equal(fs.existsSync(path.join(root, 'audio', 'songs', id + '.mp3')), false, id + ' removed recording must be absent');
  const metadataFile = path.join(root, 'audio', 'songs', 'metadata.json');
  if (!missing.length && fs.existsSync(metadataFile)) {
    const metadata = JSON.parse(fs.readFileSync(metadataFile, 'utf8'));
    assert.deepEqual(metadata.songs.map(song => song.id).sort(), [...expectedSongIds].sort());
    for (const song of metadata.songs) {
      assert.ok(assets.includes('./' + song.file), 'metadata song must be part of the offline asset list');
      const data = fs.readFileSync(path.join(root, song.file));
      assert.equal(data.length, song.validation.bytes, song.id + ' byte count');
      const hash = createHash('sha256').update(data).digest('hex');
      assert.equal(hash, song.validation.sha256, song.id + ' output hash');
      if (retainedSongHashes[song.id]) assert.equal(hash, retainedSongHashes[song.id], song.id + ' must retain the previous approved recording');
    }
    console.log('PASS all seven song payloads match their metadata byte counts and SHA-256 hashes.');
    console.log('PASS all six retained recordings are unchanged, including Sommartider and the approved Bromance chorus.');
  }
}

main().catch(error => { console.error(error.stack); process.exitCode = 1; });
