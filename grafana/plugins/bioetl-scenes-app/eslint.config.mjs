import { defineConfig } from 'eslint/config';
import grafanaConfig from '@grafana/eslint-config';
import { createPluginConfig } from '../eslint-shared-config.mjs';

export default createPluginConfig(defineConfig, grafanaConfig);
