import assert from 'node:assert/strict';
import { test } from 'node:test';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { inspectTrustedBase, parseArguments, parseVerificationArguments, validateDeliveryImage, validateImage, verifyImages as verifyImagesImpl } from './verify-host-image.mjs';

const digest = 'a'.repeat(64);
const verifyImages = (built, manifest, inspect, fingerprint, filesystem = () => digest,
  base = { RootFS: { Type: 'layers', Layers: ['sha256:' + digest] } }) =>
  verifyImagesImpl(built, manifest, inspect, fingerprint, filesystem, base);
const manifest = {
  image: 'satorykono/bioetl-grafana-router7-canvas@sha256:' + digest,
  artifact_sha256: Object.fromEntries(['bioetl-scenes-app', 'bioetl-selectorshell-panel']
    .map((plugin) => [`grafana/plugins/${plugin}/dist/module.js`, digest])),
};
const inspect = (image) => ({
  Id: 'sha256:' + (image === 'bioetl-router-host:acceptance' ? 'b' : 'c').repeat(64),
  RepoDigests: [manifest.image], Architecture: 'amd64', Os: 'linux',
  Config: { User: 'grafana', Entrypoint: ['/run.sh'] },
  RootFS: { Type: 'layers', Layers: ['sha256:' + digest] },
});
const fingerprint = () => ({ tree_sha256: digest, module_sha256: digest });

test('ordinary verification retains the declared image and explicit candidate selection is separate', () => {
  assert.deepEqual(parseVerificationArguments(['bioetl-router-host:acceptance'], manifest.image), {
    built: 'bioetl-router-host:acceptance', deliveryImage: manifest.image, candidate: false,
  });
  const image = manifest.image.replace(digest, 'b'.repeat(64));
  assert.deepEqual(parseVerificationArguments(['bioetl-router-host:acceptance', '--candidate-image', image], manifest.image), {
    built: 'bioetl-router-host:acceptance', deliveryImage: image, candidate: true,
  });
});

test('candidate selection rejects flags, mutable tags and references outside the owned repository', () => {
  for (const image of ['--help', 'grafana/grafana:latest', 'satorykono/bioetl-grafana-router7-canvas:latest',
    'foreign/image@sha256:' + digest, manifest.image + ' extra']) {
    assert.throws(() => validateDeliveryImage(image));
    assert.throws(() => parseVerificationArguments(['bioetl-router-host:acceptance', '--candidate-image', image], manifest.image));
  }
  for (const args of [['bioetl-router-host:acceptance', '--candidate-image'],
    ['bioetl-router-host:acceptance', '--output', manifest.image],
    ['bioetl-router-host:acceptance', '--candidate-image', manifest.image, 'extra']]) {
    assert.throws(() => parseVerificationArguments(args, manifest.image));
  }
});

test('source provenance generator rejects unqualified captures and preserves history', () => {
  const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
  const result = spawnSync(python, [
    'tests/unit/scripts/ops/observability/grafana/test_refresh_router_host_provenance.py', '-v',
  ], {
    cwd: fileURLToPath(new URL('../../../', import.meta.url)), encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
  });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stderr, /Ran 8 tests/);
  assert.match(result.stderr, /\bOK\b/);
});

test('trusted immutable base is pulled before inspection independently of BuildKit', () => {
  const calls = [];
  const expected = 'grafana/grafana@sha256:d84563330dc9d2fd2bc096d0fb96021b5319c75bf6ed555566709998e823dec4';
  const result = inspectTrustedBase((program, args) => {
    assert.match(program, /docker(?:\.exe)?$/);
    assert.deepEqual(args, ['pull', expected]);
    calls.push('pull');
  }, (image) => {
    assert.equal(image, expected);
    assert.deepEqual(calls, ['pull']);
    calls.push('inspect');
    return { Id: 'sha256:' + digest };
  });
  assert.deepEqual(calls, ['pull', 'inspect']);
  assert.equal(result.Id, 'sha256:' + digest);
});

test('base pull failure propagates without inspection or parity claims', () => {
  assert.throws(() => inspectTrustedBase(() => { throw new Error('registry unavailable'); },
    () => assert.fail('unavailable trusted base must not be inspected')), /registry unavailable/);
});

test('rebuilt and registry image digests are recorded separately with artifact parity', () => {
  const receipt = verifyImages('bioetl-router-host:acceptance', manifest, inspect, fingerprint);
  assert.equal(receipt.status, 'PASS');
  assert.notEqual(receipt.built_image_config_digest, receipt.declared_image_config_digest);
  assert.equal(receipt.declared_image, manifest.image);
  assert.equal(Object.keys(receipt.artifacts).length, 3);
});

test('changed frontend or plugin bytes cannot pass image parity', () => {
  for (const changed of ['public/build', 'bioetl-scenes-app', 'bioetl-selectorshell-panel']) {
    assert.throws(() => verifyImages('bioetl-router-host:acceptance', manifest, inspect, (image, scope) => ({
      ...fingerprint(), tree_sha256: image === 'bioetl-router-host:acceptance' && scope.endsWith(changed) ? 'd'.repeat(64) : digest,
    })), /Image artifact mismatch/);
  }
});

test('image contents must also match each recorded manifest bundle', () => {
  assert.throws(() => verifyImages('bioetl-router-host:acceptance', {
    ...manifest, artifact_sha256: {},
  }, inspect, fingerprint), /Manifest bundle mismatch/);
});

test('a different runtime user or uninspected registry digest is rejected', () => {
  assert.throws(() => verifyImages('bioetl-router-host:acceptance', manifest, (image) => ({
    ...inspect(image), Config: { User: image === 'bioetl-router-host:acceptance' ? 'root' : 'grafana' },
  }), fingerprint), /Image configuration mismatch/);
  assert.throws(() => verifyImages('bioetl-router-host:acceptance', manifest, (image) => ({
    ...inspect(image), RepoDigests: [],
  }), fingerprint), /Declared registry digest/);
});


test('CLI rejects Docker flags, arbitrary references and output path arguments', () => {
  for (const image of ['sha256:' + digest + '\n', manifest.image + '\n', '--privileged', '--format=json', '-q', ' image', 'image\n--privileged', '../image', 'registry.invalid/host@sha256:' + digest]) {
    assert.throws(() => validateImage(image), /Unsupported image reference/);
  }
  assert.equal(parseArguments(['bioetl-router-host:acceptance']), 'bioetl-router-host:acceptance');
  assert.equal(validateImage('sha256:' + digest), 'sha256:' + digest);
  for (const output of ['../../outside.json', '/tmp/receipt.json', 'reports/qa/receipt.json']) {
    assert.throws(() => parseArguments(['bioetl-router-host:acceptance', output]), /Usage:/);
  }
  assert.throws(() => parseArguments([]), /Usage:/);
});

test('manifest argument injection is rejected before invoking Docker callbacks', () => {
  assert.throws(() => verifyImages('bioetl-router-host:acceptance', {
    ...manifest, image: '--format=@sha256:' + digest,
  }, () => assert.fail('Docker must not execute'), fingerprint), /Unsupported image reference/);
});


test('different layer timestamps can pass with identical complete filesystem contents', () => {
  const receipt = verifyImages('bioetl-router-host:acceptance', manifest, (image) => ({
    ...inspect(image), RootFS: { Type: 'layers', Layers: ['sha256:' + digest, 'sha256:' + (image === manifest.image ? 'd' : 'a').repeat(64)] },
  }), fingerprint);
  assert.equal(receipt.status, 'PASS');
  assert.equal(receipt.rootfs_sha256, digest);
  assert.notDeepEqual(receipt.built_layers, receipt.declared_layers);
});

test('changed complete filesystem fails before any image tools execute', () => {
  assert.throws(() => verifyImages('bioetl-router-host:acceptance', manifest, inspect,
    () => assert.fail('Unverified image tools must not execute'),
    (image) => (image === manifest.image ? 'd' : 'a').repeat(64)), /Complete image filesystem mismatch/);
});

test('missing or empty rootfs evidence cannot pass', () => {
  for (const RootFS of [undefined, { Type: 'layers', Layers: [] }]) {
    assert.throws(() => verifyImages('bioetl-router-host:acceptance', manifest,
      (image) => ({ ...inspect(image), RootFS }), fingerprint), /layer/);
  }
});

test('an unrelated base cannot pass complete content parity', () => {
  assert.throws(() => verifyImages('bioetl-router-host:acceptance', manifest, inspect, fingerprint,
    () => assert.fail('Untrusted base must fail before export'),
    { RootFS: { Type: 'layers', Layers: ['sha256:' + 'd'.repeat(64)] } }), /Trusted base layer prefix mismatch/);
});
