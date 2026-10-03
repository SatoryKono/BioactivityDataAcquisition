import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parseArguments, validateImage, verifyImages } from './verify-host-image.mjs';

const digest = 'a'.repeat(64);
const manifest = {
  image: 'satorykono/bioetl-grafana-router7-canvas@sha256:' + digest,
  artifact_sha256: Object.fromEntries(['bioetl-scenes-app', 'bioetl-selectorshell-panel']
    .map((plugin) => [`grafana/plugins/${plugin}/dist/module.js`, digest])),
};
const inspect = (image) => ({
  Id: 'sha256:' + (image === 'bioetl-router-host:acceptance' ? 'b' : 'c').repeat(64),
  RepoDigests: [manifest.image], Architecture: 'amd64', Os: 'linux',
  Config: { User: 'grafana', Entrypoint: ['/run.sh'] },
});
const fingerprint = () => ({ tree_sha256: digest, module_sha256: digest });

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
