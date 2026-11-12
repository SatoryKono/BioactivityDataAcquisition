import { createHash } from 'node:crypto';
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { Compiler } from 'webpack';

const hash = (bytes: Buffer | string) => createHash('sha256').update(bytes).digest('hex');

function files(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const name = path.join(directory, entry.name);
    return entry.isDirectory() ? files(name) : [name];
  }).sort();
}

export class AdaptiveBuildProvenance {
  apply(compiler: Compiler) {
    const pluginRoot = process.cwd();
    const repoRoot = path.resolve(pluginRoot, '../../..');
    const inputPaths = () => [
      ...files(path.join(pluginRoot, 'src')),
      ...files(path.join(pluginRoot, '.config')),
      ...['package.json', 'package-lock.json', 'tsconfig.json', 'eslint.config.mjs', 'webpack.config.ts', 'webpack.adaptive.config.ts', 'adaptive-build-provenance.ts', 'README.md', 'LICENSE', 'CHANGELOG.md'].map((name) => path.join(pluginRoot, name)),
      path.join(pluginRoot, '../../tooling/router-v7-bridge/webpack-public-path.cjs'),
      path.join(pluginRoot, '../../tooling/router-v7-bridge/host-image.json'),
    ];
    const snapshot = () => Object.fromEntries(inputPaths().map((name) => [
      path.relative(repoRoot, name).replaceAll('\\', '/'),
      hash(readFileSync(name, 'utf8').replaceAll('\r\n', '\n')),
    ]));
    const before = snapshot();
    compiler.hooks.done.tap('BioetlAdaptiveBuildProvenance', (stats) => {
      if (stats.hasErrors()) {
        throw new Error('Adaptive plugin compilation failed; no provenance receipt written');
      }
      if (JSON.stringify(before) !== JSON.stringify(snapshot())) {
        throw new Error('Adaptive plugin inputs changed during compilation');
      }
      const output = path.resolve(pluginRoot, 'dist-adaptive');
      const outputs = Object.fromEntries(files(output)
        .filter((name) => !name.endsWith('build-provenance.json'))
        .map((name) => [path.relative(output, name).replaceAll('\\', '/'), hash(readFileSync(name))]));
      writeFileSync(path.join(output, 'build-provenance.json'), JSON.stringify({
        schema_version: 1,
        capability: 'adaptive-table-v1',
        inputs_sha256_lf: before,
        outputs_sha256: outputs,
      }, null, 2) + '\n');
    });
  }
}
