'use strict';

// Pure checks for the offline asset manifest and HTTP byte ranges.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const code = fs.readFileSync(path.join(root, 'sw.js'), 'utf8');
const context = vm.createContext({ self: { addEventListener() {} }, URL, Request, Response });
new vm.Script(code, { filename: 'sw.js' }).runInContext(context);
const rangeResponse = vm.runInContext('audioRange', context);
const assets = Array.from(vm.runInContext('ASSETS', context));
const version = vm.runInContext('VERSION', context);
assert.equal(version, '4.4');
assert.ok(assets.includes('./app-v4.4.js'));
assert.equal(assets.filter(asset => asset.startsWith('./audio/songs/')).length, 6);
assert.equal(assets.filter(asset => /^\.\/audio\/[^/]+\.mp3$/.test(asset)).length, 9);
assert.equal(new Set(assets).size, assets.length);
new vm.Script(fs.readFileSync(path.join(root, 'app-v4.4.js'), 'utf8'), { filename: 'app-v4.4.js' });
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
assert.match(html, /app-v4\.4\.js/);
assert.match(html, /Version 4\.4/);

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
  console.log('PASS app/service-worker syntax, version references, complete fifteen-recording manifest, byte ranges, suffix ranges, and invalid ranges.');
  if (missing.length) console.log('Manifest files still pending: ' + missing.join(', '));
  else console.log('PASS all manifest assets exist.');
  if (process.argv.includes('--require-assets')) assert.deepEqual(missing, [], 'every offline asset must be present');
}

main().catch(error => { console.error(error.stack); process.exitCode = 1; });
