import { createHash } from 'node:crypto';
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { AdaptiveBuildProvenance } from '../adaptive-build-provenance';

jest.mock('node:fs', () => ({
  readdirSync: jest.fn(() => []),
  readFileSync: jest.fn(),
  writeFileSync: jest.fn(),
}));

const copiedFiles = ['README.md', 'LICENSE', 'CHANGELOG.md'];
const hostManifest = path.resolve('../../tooling/router-v7-bridge/host-image.json');

function startBuild(contents, hasErrors = false) {
  jest.mocked(readFileSync).mockImplementation((name) => contents.get(String(name)) ?? 'unchanged');
  let complete = () => { throw new Error('Build hook was not registered'); };
  const compiler = {
    hooks: { done: { tap: (_name, callback) => { complete = callback; } } },
  };
  new AdaptiveBuildProvenance().apply(compiler);
  return () => complete({ hasErrors: () => hasErrors });
}

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(readdirSync).mockReturnValue([]);
});

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

test('a compiler error rejects the receipt even when input files are unchanged', () => {
  const complete = startBuild(new Map(), true);
  expect(complete).toThrow('Adaptive plugin compilation failed');
  expect(writeFileSync).not.toHaveBeenCalled();
});

test('receipt hashes the host-image manifest used by the base webpack configuration', () => {
  startBuild(new Map([[hostManifest, '{"image":"qualified"}\r\n']]))();
  const receipt = JSON.parse(String(jest.mocked(writeFileSync).mock.calls[0][1]));
  expect(receipt.inputs_sha256_lf['grafana/tooling/router-v7-bridge/host-image.json'])
    .toBe(createHash('sha256').update('{"image":"qualified"}\n').digest('hex'));
});

test('changing the host-image manifest during compilation rejects the receipt', () => {
  const contents = new Map([[hostManifest, 'original']]);
  const complete = startBuild(contents);
  contents.set(hostManifest, 'changed');
  expect(complete).toThrow('Adaptive plugin inputs changed during compilation');
  expect(writeFileSync).not.toHaveBeenCalled();
});

test('adding a source file during compilation rejects the receipt', () => {
  const complete = startBuild(new Map());
  jest.mocked(readdirSync).mockImplementation((directory) => String(directory).endsWith('src')
    ? [{ name: 'added.ts', isDirectory: () => false }] : []);
  expect(complete).toThrow('Adaptive plugin inputs changed during compilation');
  expect(writeFileSync).not.toHaveBeenCalled();
});
