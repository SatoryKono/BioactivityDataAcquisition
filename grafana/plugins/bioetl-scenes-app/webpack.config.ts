import path from 'path';

import baseConfig, { type Env } from './.config/webpack/webpack.config.ts';

export default async (env: Env) => {
  const config = await baseConfig(env);
  // This plugin has one entrypoint; absolute Windows paths are not glob patterns.
  return { ...config, entry: { module: path.resolve('src/module.tsx') } };
};
