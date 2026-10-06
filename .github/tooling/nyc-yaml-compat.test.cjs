'use strict';

// The NYC loader uses only js-yaml.load. Exercise that consumer API before
// replacing its obsolete YAML 3 -> argparse 1 -> sprintf-js dependency chain.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { createRequire } = require('node:module');
const { test } = require('node:test');
const consumer = createRequire(path.resolve('package.json'));
const loaderRequire = createRequire(consumer.resolve('@istanbuljs/load-nyc-config'));
const { loadNycConfig, isLoading } = consumer('@istanbuljs/load-nyc-config');

async function fixture(callback) {
  const cwd = await fs.mkdtemp(path.join(os.tmpdir(), 'bioetl-nyc-yaml-'));
  try {
    await fs.writeFile(path.join(cwd, 'package.json'), '{"name":"nyc-fixture"}');
    await callback(cwd);
  } finally {
    await fs.rm(cwd, { recursive: true, force: true });
  }
}

test('the installed NYC loader uses YAML 4 without the vulnerable formatter', () => {
  assert.equal(loaderRequire('js-yaml/package.json').version, '4.3.2');
  assert.throws(() => consumer.resolve('sprintf-js'), { code: 'MODULE_NOT_FOUND' });
});

test('YAML and JSON NYC options produce identical results', async () => {
  await fixture(async (cwd) => {
    await fs.writeFile(path.join(cwd, '.nycrc.yaml'),
      'all: true\ncheck-coverage: true\nlines: 80\ninclude:\n  - "src/**/*.js"\nexclude: "**/*.test.js"\nextension: .ts\n');
    await fs.writeFile(path.join(cwd, '.nycrc.json'), JSON.stringify({
      all: true, 'check-coverage': true, lines: 80,
      include: ['src/**/*.js'], exclude: '**/*.test.js', extension: '.ts',
    }));
    const yaml = await loadNycConfig({ cwd, nycrcPath: '.nycrc.yaml' });
    assert.deepEqual(yaml, await loadNycConfig({ cwd, nycrcPath: '.nycrc.json' }));
    assert.equal(yaml.checkCoverage, true);
    assert.deepEqual(yaml.exclude, ['**/*.test.js']);
    assert.deepEqual(yaml.extension, ['.ts']);
  });
});

test('YAML extensions retain inherited configuration and explicit overrides', async () => {
  await fixture(async (cwd) => {
    await fs.writeFile(path.join(cwd, 'base.yaml'), 'lines: 80\nall: true\nexclude: ["vendor/**"]\n');
    await fs.writeFile(path.join(cwd, '.nycrc.yaml'), 'extends: ./base.yaml\nbranches: 70\n');
    assert.deepEqual(await loadNycConfig({ cwd, nycrcPath: '.nycrc.yaml' }), {
      cwd, lines: 80, all: true, exclude: ['vendor/**'], branches: 70,
    });
  });
});

test('invalid YAML rejects and resets the loading state', async () => {
  await fixture(async (cwd) => {
    await fs.writeFile(path.join(cwd, '.nycrc.yaml'), 'include: [unfinished');
    await assert.rejects(loadNycConfig({ cwd, nycrcPath: '.nycrc.yaml' }), /unexpected end/);
    assert.equal(isLoading(), false);
  });
});

test('duplicate YAML keys reject instead of silently changing coverage options', async () => {
  await fixture(async (cwd) => {
    await fs.writeFile(path.join(cwd, '.nycrc.yaml'), 'lines: 80\nlines: 0\n');
    await assert.rejects(loadNycConfig({ cwd, nycrcPath: '.nycrc.yaml' }), /duplicated mapping key/);
  });
});

test('unsafe JavaScript YAML tags reject', async () => {
  await fixture(async (cwd) => {
    await fs.writeFile(path.join(cwd, '.nycrc.yaml'), 'all: !!js/function "function () { return true; }"');
    await assert.rejects(loadNycConfig({ cwd, nycrcPath: '.nycrc.yaml' }), /unknown tag/);
  });
});
