import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, constants, lstatSync, mkdirSync, openSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const scopes = [
  '/usr/share/grafana/public/build',
  '/usr/share/grafana/data/plugins-bundled/bioetl-scenes-app',
  '/usr/share/grafana/data/plugins-bundled/bioetl-selectorshell-panel',
];
const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');

// Fixed trusted executable locations; do not resolve commands through caller PATH.
const docker = process.platform === 'win32'
  ? 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' : '/usr/bin/docker';

export function validateImage(image) {
  assert.ok(typeof image === 'string' && !/\s/.test(image) && (
    image === 'bioetl-router-host:acceptance' || /^sha256:[0-9a-f]{64}$/.test(image) ||
    /^satorykono\/bioetl-grafana-router7-canvas@sha256:[0-9a-f]{64}$/.test(image)
  ), 'Unsupported image reference');
  return image;
}

export function parseArguments(args) {
  assert.equal(args.length, 1, 'Usage: verify-host-image.mjs IMAGE (receipt: reports/qa/router-v7-image-parity.json)');
  return validateImage(args[0]);
}

function writeReceipt(receipt) {
  const root = realpathSync(fileURLToPath(new URL('../../../', import.meta.url)));
  const reports = join(root, 'reports');
  assert.equal(realpathSync(reports), reports, 'Reports directory must not redirect writes');
  const directory = join(reports, 'qa');
  mkdirSync(directory, { recursive: true });
  assert.equal(realpathSync(directory), directory, 'Receipt directory must not redirect writes');
  const target = join(directory, 'router-v7-image-parity.json');
  const existing = lstatSync(target, { throwIfNoEntry: false });
  assert.ok(!existing || (existing.isFile() && existing.nlink === 1), 'Receipt must be a regular file with no additional links');
  const fd = openSync(target, constants.O_WRONLY | constants.O_CREAT | constants.O_TRUNC | (constants.O_NOFOLLOW ?? 0), 0o600);
  try { writeFileSync(fd, JSON.stringify(receipt, null, 2) + '\n'); }
  finally { closeSync(fd); }
}

export function verifyImages(built, manifest, inspect, fingerprint) {
  validateImage(built);
  validateImage(manifest.image);
  assert.match(manifest.image, /^satorykono\/bioetl-grafana-router7-canvas@sha256:[0-9a-f]{64}$/);
  const actual = inspect(built);
  const expected = inspect(manifest.image);
  assert.ok(expected.RepoDigests.includes(manifest.image), 'Declared registry digest was not inspected');
  assert.match(actual.Id, /^sha256:[0-9a-f]{64}$/);
  for (const key of ['Architecture', 'Os', 'Config']) {
    assert.deepEqual(actual[key], expected[key], `Image configuration mismatch: ${key}`);
  }
  // Docker verifies layer digests on pull. Compare the complete ordered diff-ID
  // chain before running any executable from either image, including hash tools.
  assert.equal(actual.RootFS?.Type, 'layers', 'Built image must expose layer digests');
  assert.ok(actual.RootFS.Layers?.length > 0, 'Built image layers must not be empty');
  for (const layer of actual.RootFS.Layers) assert.match(layer, /^sha256:[0-9a-f]{64}$/);
  assert.deepEqual(actual.RootFS, expected.RootFS, 'Complete image RootFS mismatch');
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
    rootfs: actual.RootFS, artifacts,
  };
}

function inspect(image) {
  return JSON.parse(execFileSync(docker, ['image', 'inspect', validateImage(image)], { encoding: 'utf8' }))[0];
}

function fingerprint(image, scope) {
  // Ignore creation times, but retain every filename, byte, type, owner, mode
  // and symlink target. Registry manifest and image-config digests differ.
  const command = 'set -o pipefail; cd "$1"; find . -type f -exec sha256sum {} + | LC_ALL=C sort; ' +
    'find . -exec stat -c "%F %u:%g %a %N" {} + | LC_ALL=C sort';
  const output = execFileSync(docker, [
    'run', '--rm', '--network', 'none', '--entrypoint', 'sh', validateImage(image),
    '-ec', command, 'verify-artifacts', scope,
  ], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
  const module = output.split('\n').find((line) => /^[0-9a-f]{64}\s+\.\/module\.js$/.test(line));
  return { tree_sha256: sha256(output), module_sha256: module?.split(/\s+/)[0] ?? null };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const manifest = JSON.parse(readFileSync(new URL('./host-image.json', import.meta.url), 'utf8'));
  const recipe = readFileSync(new URL('./Dockerfile.host', import.meta.url));
  assert.equal(sha256(recipe), manifest.artifact_sha256['grafana/tooling/router-v7-bridge/Dockerfile.host']);
  const built = parseArguments(process.argv.slice(2));
  const receipt = verifyImages(built, manifest, inspect, fingerprint);
  writeReceipt(receipt);
  console.log('Built host image matches the declared image artifact set');
}
