#!/usr/bin/env node
'use strict';

// Validate before npm ci, using the semver implementation shipped with npm.
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { execFileSync } = require('node:child_process');

function npmSemver() {
  const candidates = [
    path.join(path.dirname(process.execPath), 'node_modules/npm/package.json'),
    path.resolve(path.dirname(process.execPath), '../lib/node_modules/npm/package.json'),
    '/usr/share/nodejs/npm/package.json',
  ];
  if (process.env.npm_execpath) candidates.unshift(path.resolve(process.env.npm_execpath, '../../package.json'));
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return createRequire(candidate)('semver');
  }
  const command = process.platform === 'win32' ? process.env.ComSpec : 'npm';
  const args = process.platform === 'win32' ? ['/d', '/s', '/c', 'npm root --global'] : ['root', '--global'];
  const root = execFileSync(command, args, { encoding: 'utf8' }).trim();
  return createRequire(path.join(root, 'npm/package.json'))('semver');
}

function validateLock(manifest, lock, nodeVersion = process.versions.node) {
  const semver = npmSemver();
  const root = lock.packages && lock.packages[''];
  if (!root) throw new Error('Root npm lock is missing packages[""]');
  for (const group of ['dependencies', 'devDependencies', 'optionalDependencies']) {
    const wanted = manifest[group] || {};
    const locked = root[group] || {};
    if (JSON.stringify(Object.entries(wanted).sort()) !== JSON.stringify(Object.entries(locked).sort())) {
      throw new Error(`Root manifest/lock mismatch: ${group}`);
    }
    for (const [name, spec] of Object.entries(wanted)) {
      const entry = lock.packages[`node_modules/${name}`];
      if (!entry || !semver.satisfies(entry.version, spec)) throw new Error(`Invalid locked version for ${name}: ${spec}`);
    }
  }
  for (const [name, entry] of Object.entries({ '<root>': manifest, ...lock.packages })) {
    const range = entry.engines && entry.engines.node;
    if (range && !semver.satisfies(nodeVersion, range)) {
      throw new Error(`Unsupported Node ${nodeVersion}: ${name || '<root>'} requires ${range}`);
    }
  }
  return lock.packages['node_modules/playwright'].version;
}

function validateBrowser({ expectedVersion, installedVersion, coreVersion, expectedBrowserVersion, browserVersion, executableExists }) {
  if (installedVersion !== expectedVersion || coreVersion !== expectedVersion) throw new Error('Playwright package/core/lock version mismatch');
  if (!executableExists) throw new Error('Matching Playwright browser executable is missing; rebuild/install Chromium');
  if (browserVersion !== expectedBrowserVersion) throw new Error(`Chromium version mismatch: expected ${expectedBrowserVersion}, got ${browserVersion}`);
}

async function verifyBrowser(root, modulesRoot) {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  const lock = JSON.parse(fs.readFileSync(path.join(root, 'package-lock.json'), 'utf8'));
  const expectedVersion = validateLock(manifest, lock);
  const runtimeRequire = createRequire(path.join(modulesRoot, 'playwright/package.json'));
  const playwright = runtimeRequire('playwright');
  const core = JSON.parse(fs.readFileSync(path.join(modulesRoot, 'playwright-core/package.json'), 'utf8'));
  const browsers = JSON.parse(fs.readFileSync(path.join(modulesRoot, 'playwright-core/browsers.json'), 'utf8'));
  const expected = browsers.browsers.find((browser) => browser.name === 'chromium');
  const installed = runtimeRequire('playwright/package.json').version;
  // Reject stale packages before attempting to launch a browser or contact Grafana.
  if (installed !== expectedVersion || core.version !== expectedVersion) throw new Error('Playwright package/core/lock version mismatch');
  const executableExists = fs.existsSync(playwright.chromium.executablePath());
  if (!executableExists) throw new Error('Matching Playwright browser executable is missing; rebuild/install Chromium');
  const browser = await playwright.chromium.launch({ headless: true });
  try {
    validateBrowser({ expectedVersion, installedVersion: installed, coreVersion: core.version,
      expectedBrowserVersion: expected.browserVersion, browserVersion: browser.version(), executableExists });
  } finally { await browser.close(); }
}

module.exports = { validateLock, validateBrowser, verifyBrowser };
if (require.main === module) {
  const [root, mode, modulesRoot] = process.argv.slice(2);
  Promise.resolve().then(() => {
    if (mode === '--browser') return verifyBrowser(root, modulesRoot);
    const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
    const lock = JSON.parse(fs.readFileSync(path.join(root, 'package-lock.json'), 'utf8'));
    const version = validateLock(manifest, lock);
    if (mode === '--playwright-version') console.log(version);
  }).catch((error) => { console.error(error.message); process.exitCode = 1; });
}
