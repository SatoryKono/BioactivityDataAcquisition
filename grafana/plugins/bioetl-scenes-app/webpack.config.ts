import path from 'path';
import fs from 'fs';
import ReplaceInFileWebpackPlugin from 'replace-in-file-webpack-plugin';

import baseConfig, { type Env } from './.config/webpack/webpack.config.ts';

export default async (env: Env) => {
  const config = await baseConfig(env);
  const manifest = JSON.parse(fs.readFileSync(path.resolve('../../tooling/router-v7-bridge/host-image.json'), 'utf8'));
  const releaseDate: string = manifest.plugin_release_date;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(releaseDate) || new Date(releaseDate).toISOString().slice(0, 10) !== releaseDate) {
    throw new Error('host-image.json requires a valid plugin_release_date');
  }
  const pluginVersion: string = JSON.parse(fs.readFileSync(path.resolve('package.json'), 'utf8')).version;
  const pluginId: string = JSON.parse(fs.readFileSync(path.resolve('src/plugin.json'), 'utf8')).id;
  const plugins = config.plugins?.map((plugin) => plugin instanceof ReplaceInFileWebpackPlugin
    ? new ReplaceInFileWebpackPlugin([{
      dir: path.resolve('dist'),
      test: [/(^|\/)plugin\.json$/, /(^|\/)README\.md$/],
      rules: [
        { search: /%VERSION%/g, replace: pluginVersion },
        { search: /%TODAY%/g, replace: releaseDate },
        { search: /%PLUGIN_ID%/g, replace: pluginId },
      ],
    }])
    : plugin);
  // This plugin has one entrypoint; absolute Windows paths are not glob patterns.
  return { ...config, plugins, entry: { module: path.resolve('src/module.tsx') } };
};
