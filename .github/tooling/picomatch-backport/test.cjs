'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');

const root = process.argv[2] ? path.resolve(process.argv[2]) : __dirname;
const picomatch = require(path.join(root, 'node_modules', 'picomatch'));

assert.equal(picomatch.makeRe('*.js').test('a.js'), true);
assert.equal(picomatch.makeRe('*.js').test('a.md'), false);
assert.equal(require(path.join(root, 'node_modules', 'picomatch', 'package.json')).version, '4.0.8-bioetl.15');
console.log('picomatch backport ok');
