import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const scopes = [
  '/usr/share/grafana/public/build',
  '/usr/share/grafana/data/plugins-bundled/bioetl-scenes-app',
  '/usr/share/grafana/data/plugins-bundled/bioetl-selectorshell-panel',
];
const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');

export function verifyImages(built, manifest, inspect, fingerprint) {
  assert.match(manifest.image, /@sha256:[0-9a-f]{64}$/);
  const actual = inspect(built);
  const expected = inspect(manifest.image);
  assert.ok(expected.RepoDigests.includes(manifest.image), 'Declared registry digest was not inspected');
  assert.match(actual.Id, /^sha256:[0-9a-f]{64}$/);
  for (const key of ['Architecture', 'Os', 'Config']) {
    assert.deepEqual(actual[key], expected[key], `Image configuration mismatch: ${key}`);
  }
  const artifacts = {};
  for (const scope of scopes) {
    const produced = fingerprint(built, scope);
    assert.deepEqual(produced, fingerprint(manifest.image, scope), `Image artifact mismatch: ${scope}`);
    if (scope.includes('/plugins-bundled/')) {
      const plugin = scope.split('/').at(-1);
      assert.equal(produced.module_sha256,
        manifest.artifact_sha256[`grafana/plugins/${plugin}/dist/module.js`],
        `Manifest bundle mismatch: ${plugin}`);
    }
    artifacts[scope] = produced;
  }
  return {
    status: 'PASS', built_image_config_digest: actual.Id,
    declared_image: manifest.image, declared_image_config_digest: expected.Id,
    artifacts,
  };
}

function inspect(image) {
  return JSON.parse(execFileSync('docker', ['image', 'inspect', image], { encoding: 'utf8' }))[0];
}

function fingerprint(image, scope) {
  // Ignore creation times, but retain every filename, byte, type, owner, mode
  // and symlink target. Registry manifest and image-config digests differ.
  const command = 'set -o pipefail; cd "$1"; find . -type f -exec sha256sum {} + | LC_ALL=C sort; ' +
    'find . -exec stat -c "%F %u:%g %a %N" {} + | LC_ALL=C sort';
  const output = execFileSync('docker', [
    'run', '--rm', '--network', 'none', '--entrypoint', 'sh', image,
    '-ec', command, 'verify-artifacts', scope,
  ], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
  const module = output.split('\n').find((line) => /^[0-9a-f]{64}\s+\.\/module\.js$/.test(line));
  return { tree_sha256: sha256(output), module_sha256: module?.split(/\s+/)[0] ?? null };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const manifest = JSON.parse(readFileSync(new URL('./host-image.json', import.meta.url), 'utf8'));
  const recipe = readFileSync(new URL('./Dockerfile.host', import.meta.url));
  assert.equal(sha256(recipe), manifest.artifact_sha256['grafana/tooling/router-v7-bridge/Dockerfile.host']);
  assert.ok(process.argv[2] && process.argv[3], 'Usage: verify-host-image.mjs IMAGE RECEIPT.json');
  const receipt = verifyImages(process.argv[2], manifest, inspect, fingerprint);
  writeFileSync(process.argv[3], JSON.stringify(receipt, null, 2) + '\n');
  console.log('Built host image matches the declared image artifact set');
}
