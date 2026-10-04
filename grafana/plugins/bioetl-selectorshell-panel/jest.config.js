// force timezone to UTC to allow tests to work regardless of local timezone
// generally used by snapshots, but can affect specific tests
process.env.TZ = 'UTC';

module.exports = {
  // Jest configuration provided by Grafana scaffolding
  ...require('./.config/jest.config'),
  // Relative globs avoid Jest escaping the .codex ancestor on Windows.
  testMatch: ['**/src/**/__tests__/**/*.{js,jsx,ts,tsx}', '**/src/**/*.{spec,test,jest}.{js,jsx,ts,tsx}'],
};
