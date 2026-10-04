// force timezone to UTC to allow tests to work regardless of local timezone
// generally used by snapshots, but can affect specific tests
process.env.TZ = 'UTC';

const scaffold = require('./.config/jest.config');
const { grafanaESModules, nodeModulesToTransform } = require('./.config/jest/utils');

module.exports = {
  // Jest configuration provided by Grafana scaffolding
  ...scaffold,
  // Execute the actual ESM bridge when tests import Grafana runtime/Scenes.
  transform: {
    ...scaffold.transform,
    '^.+\\.mjs$': ['@swc/jest', { jsc: { parser: { syntax: 'ecmascript' } } }],
  },
  transformIgnorePatterns: [nodeModulesToTransform([...grafanaESModules, 'react-router-dom-v5-compat', '@react-hookz/web', '@ver0/deep-equal'])],
  // Relative globs avoid Jest escaping the .codex ancestor on Windows.
  testMatch: ['**/src/**/__tests__/**/*.{js,jsx,ts,tsx}', '**/src/**/*.{spec,test,jest}.{js,jsx,ts,tsx}'],
};
