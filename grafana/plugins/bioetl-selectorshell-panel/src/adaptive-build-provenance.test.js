import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { AdaptiveBuildProvenance } from '../adaptive-build-provenance';

jest.mock('node:fs', () => ({
  readdirSync: jest.fn(() => []),
  readFileSync: jest.fn(),
  writeFileSync: jest.fn(),
}));

const copiedFiles = ['README.md', 'LICENSE', 'CHANGELOG.md'];

function startBuild(contents) {
  jest.mocked(readFileSync).mockImplementation((name) => contents.get(String(name)) ?? 'unchanged');
  let complete = () => { throw new Error('Build hook was not registered'); };
  const compiler = {
    hooks: { done: { tap: (_name, callback) => { complete = callback; } } },
  };
  new AdaptiveBuildProvenance().apply(compiler);
  return () => complete();
}

beforeEach(() => jest.clearAllMocks());

test('receipt includes LF-normalized hashes of the three root files copied into the bundle', () => {
  const contents = new Map(copiedFiles.map((name) => [path.resolve(name), `${name}\r\ncontent\r\n`]));
  startBuild(contents)();
  const receipt = JSON.parse(String(jest.mocked(writeFileSync).mock.calls[0][1]));
  for (const name of copiedFiles) {
    const relative = `grafana/plugins/bioetl-selectorshell-panel/${name}`;
    const expected = createHash('sha256').update(`${name}\ncontent\n`).digest('hex');
    expect(receipt.inputs_sha256_lf[relative]).toBe(expected);
  }
});

test.each(copiedFiles)('changing copied %s during compilation rejects the receipt', (name) => {
  const contents = new Map([[path.resolve(name), 'original']]);
  const complete = startBuild(contents);
  contents.set(path.resolve(name), 'changed');
  expect(complete).toThrow('Adaptive plugin inputs changed during compilation');
  expect(writeFileSync).not.toHaveBeenCalled();
});
