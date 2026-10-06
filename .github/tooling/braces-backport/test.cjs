'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const { createRequire } = require('node:module');
const consumer = createRequire(path.resolve(process.argv[2], 'package.json'));
const braces = consumer('braces');

assert.equal(consumer('braces/package.json').version, '3.0.4-bioetl.1');
for (const delimiter of [['{', '}'], ['(', ')']]) {
  const input = delimiter[0].repeat(101) + 'a,b' + delimiter[1].repeat(101);
  assert.throws(() => braces.parse(input), /exceeds max depth/);
  assert.throws(() => braces.parse(input, { maxDepth: Infinity }), /exceeds max depth/);
  assert.throws(() => braces.parse(input, { maxDepth: 1000 }), /exceeds max depth/);
}
for (const api of ['compile', 'expand', 'stringify']) {
  let ast = { type: 'text', value: 'a' };
  for (let i = 0; i < 101; i++) ast = { type: 'brace', nodes: [ast] };
  assert.throws(() => braces[api]({ type: 'root', nodes: [ast] }), /exceeds max depth/);
}
const cyclic = { type: 'paren', nodes: [{ type: 'text', value: 'a' }] };
cyclic.parent = cyclic;
assert.throws(() => braces.expand(cyclic), /parent chain contains a cycle/);
assert.throws(() => braces.parse('{{a,b},c}', { maxDepth: 1.5 }), /exceeds max depth/);
assert.deepEqual(braces.expand('foo/({a,b})'), ['foo/(a)', 'foo/(b)']);
assert.equal(braces.stringify(braces.parse('{a,{b,{c}}}'), { escapeInvalid: true }), '{a,{b,{c}}}');
console.log('braces backport: installed consumer security and compatibility checks passed');
