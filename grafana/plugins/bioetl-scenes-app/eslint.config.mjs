import { defineConfig } from 'eslint/config';
import grafanaConfig from '@grafana/eslint-config';

export default defineConfig([
  {
    ignores: [
      '**/logs',
      '**/*.log',
      '**/npm-debug.log*',
      '**/yarn-debug.log*',
      '**/yarn-error.log*',
      '**/.pnpm-debug.log*',
      '**/node_modules/',
      '.yarn/cache',
      '.yarn/unplugged',
      '.yarn/build-state.yml',
      '.yarn/install-state.gz',
      '**/.pnp.*',
      '**/pids',
      '**/*.pid',
      '**/*.seed',
      '**/*.pid.lock',
      '**/lib-cov',
      '**/coverage',
      '**/dist/',
      '**/artifacts/',
      '**/work/',
      '**/ci/',
      'test-results/',
      'playwright-report/',
      'blob-report/',
      'playwright/.cache/',
      'playwright/.auth/',
      '**/.idea',
      '**/.eslintcache',
    ],
  },
  // Preserve the scaffold overrides while using Grafana's exported flat config.
  ...grafanaConfig,
  { rules: { 'react/prop-types': 'off' } },
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: { parserOptions: { project: './tsconfig.json' } },
    rules: { '@typescript-eslint/no-deprecated': 'warn' },
  },
  {
    files: ['./tests/**/*'],
    rules: { 'react-hooks/rules-of-hooks': 'off' },
  },
]);
