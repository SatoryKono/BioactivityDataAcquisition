import path from 'path';
import ReplaceInFileWebpackPlugin from 'replace-in-file-webpack-plugin';
import baseConfig from './webpack.config';
import type { Env } from './.config/webpack/webpack.config';
import { AdaptiveBuildProvenance } from './adaptive-build-provenance';

export default async (env: Env) => {
  const config = await baseConfig(env);
  return {
    ...config,
    entry: { module: path.resolve('src/adaptive-module.ts') },
    output: { ...config.output, path: path.resolve('dist-adaptive') },
    plugins: [...(config.plugins?.map((plugin) => plugin instanceof ReplaceInFileWebpackPlugin
      ? new ReplaceInFileWebpackPlugin([{
        dir: path.resolve('dist-adaptive'),
        test: [/(^|\/)plugin\.json$/, /(^|\/)README\.md$/],
        rules: [
          { search: /%VERSION%/g, replace: '1.1.2' },
          { search: /%TODAY%/g, replace: '2026-11-12' },
          { search: /%PLUGIN_ID%/g, replace: 'bioetl-selectorshell-panel' },
          { search: /"keywords":\s*\[\s*"panel"\s*\]/g, replace: '"keywords": ["panel", "adaptive-table-v1"]' },
          { search: /"name": "Selector-Shell"/g, replace: '"name": "BioETL Adaptive Table"' },
          { search: /"description":\s*"[^"]*"/g, replace: '"description": "Responsive tables with complete details and a compatible selector shell."' },
          { search: /"updated": "2026-10-03"/g, replace: '"updated": "2026-11-12"' },
        ],
      }])
      : plugin) ?? []), new AdaptiveBuildProvenance()],
  };
};
