import assert from 'node:assert/strict';
import fs from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.dirname(fileURLToPath(import.meta.url));
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const filename = `${manifest.name.replace(/^@/, '').replace('/', '-')}-${manifest.version}.tgz`;
const tar = gunzipSync(fs.readFileSync(path.join(root, filename)));
const entries = new Map();
for (let offset = 0; offset + 512 <= tar.length; ) {
  const header = tar.subarray(offset, offset + 512);
  const name = header.subarray(0, 100).toString().replace(/\0.*$/, '');
  if (!name) break;
  const size = parseInt(header.subarray(124, 136).toString().replace(/\0.*$/, '').trim(), 8);
  assert.ok(Number.isSafeInteger(size) && size >= 0 && offset + 512 + size <= tar.length, 'Invalid tar member');
  entries.set(name, tar.subarray(offset + 512, offset + 512 + size));
  offset += 512 + Math.ceil(size / 512) * 512;
}
for (const name of ['index.mjs', 'index.d.ts', 'README.md']) {
  const packed = entries.get('package/' + name)?.toString('utf8').replace(/\r\n/g, '\n');
  const source = fs.readFileSync(path.join(root, name), 'utf8').replace(/\r\n/g, '\n');
  assert.equal(packed, source, `Stale packed ${name}`);
}
assert.deepEqual(JSON.parse(entries.get('package/package.json')), manifest, 'Stale packed package metadata');
assert.deepEqual([...entries.keys()].sort(), ['package/README.md', 'package/index.d.ts', 'package/index.mjs', 'package/package.json']);
console.log(`Packed bridge matches its canonical source: ${filename}`);
