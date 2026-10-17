'use strict';

// Pure checks for the offline asset manifest and HTTP byte ranges.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { createHash } = require('node:crypto');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const expectedSongIds = ['greta-gris', 'bjornen-sover', 'baby-shark', 'en-livstid-i-krig', 'bromance', 'sommartider', 'sandstorm', 'ring-of-fire', 'the-final-countdown', 'imperial-march', 'seven-nation-army', 'through-the-fire-and-flames'];
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
const code = fs.readFileSync(path.join(root, 'sw.js'), 'utf8');
const context = vm.createContext({ self: { addEventListener() {} }, URL, Request, Response });
new vm.Script(code, { filename: 'sw.js' }).runInContext(context);
const rangeResponse = vm.runInContext('audioRange', context);
const assets = Array.from(vm.runInContext('ASSETS', context));
const version = vm.runInContext('VERSION', context);
assert.equal(version, '5.3');
assert.ok(assets.includes('./app-v4.4.js'));
assert.ok(assets.includes('./song-icons.svg'), 'the song illustrations are available offline');
assert.deepEqual(assets.filter(asset => asset.startsWith('./audio/songs/')).sort(), expectedSongIds.map(id => './audio/songs/' + id + '.mp3').sort());
assert.equal(assets.filter(asset => /^\.\/audio\/[^/]+\.mp3$/.test(asset)).length, 9);
assert.equal(new Set(assets).size, assets.length);
assert.equal(assets.length, 37);
new vm.Script(fs.readFileSync(path.join(root, 'app-v4.4.js'), 'utf8'), { filename: 'app-v4.4.js' });
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
assert.match(html, /app-v4\.4\.js/);
assert.match(html, /Version 5\.3/);

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
  console.log('PASS app/service-worker syntax, version references, complete twenty-one-recording manifest, byte ranges, suffix ranges, and invalid ranges.');
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
    console.log('PASS all twelve song payloads match their metadata byte counts and SHA-256 hashes.');
    console.log('PASS all twelve approved recordings are byte-for-byte unchanged.');
  }
}

main().catch(error => { console.error(error.stack); process.exitCode = 1; });
