import assert from 'node:assert/strict';
import { test } from 'node:test';
import { verifyImages } from './verify-host-image.mjs';

const digest = 'a'.repeat(64);
const manifest = {
  image: 'registry.invalid/host@sha256:' + digest,
  artifact_sha256: Object.fromEntries(['bioetl-scenes-app', 'bioetl-selectorshell-panel']
    .map((plugin) => [`grafana/plugins/${plugin}/dist/module.js`, digest])),
};
const inspect = (image) => ({
  Id: 'sha256:' + (image === 'built' ? 'b' : 'c').repeat(64),
  RepoDigests: [manifest.image], Architecture: 'amd64', Os: 'linux',
  Config: { User: 'grafana', Entrypoint: ['/run.sh'] },
});
const fingerprint = () => ({ tree_sha256: digest, module_sha256: digest });

test('rebuilt and registry image digests are recorded separately with artifact parity', () => {
  const receipt = verifyImages('built', manifest, inspect, fingerprint);
  assert.equal(receipt.status, 'PASS');
  assert.notEqual(receipt.built_image_config_digest, receipt.declared_image_config_digest);
  assert.equal(receipt.declared_image, manifest.image);
  assert.equal(Object.keys(receipt.artifacts).length, 3);
});

test('changed frontend or plugin bytes cannot pass image parity', () => {
  for (const changed of ['public/build', 'bioetl-scenes-app', 'bioetl-selectorshell-panel']) {
    assert.throws(() => verifyImages('built', manifest, inspect, (image, scope) => ({
      ...fingerprint(), tree_sha256: image === 'built' && scope.endsWith(changed) ? 'd'.repeat(64) : digest,
    })), /Image artifact mismatch/);
  }
});

test('image contents must also match each recorded manifest bundle', () => {
  assert.throws(() => verifyImages('built', {
    ...manifest, artifact_sha256: {},
  }, inspect, fingerprint), /Manifest bundle mismatch/);
});

test('a different runtime user or uninspected registry digest is rejected', () => {
  assert.throws(() => verifyImages('built', manifest, (image) => ({
    ...inspect(image), Config: { User: image === 'built' ? 'root' : 'grafana' },
  }), fingerprint), /Image configuration mismatch/);
  assert.throws(() => verifyImages('built', manifest, (image) => ({
    ...inspect(image), RepoDigests: [],
  }), fingerprint), /Declared registry digest/);
});
