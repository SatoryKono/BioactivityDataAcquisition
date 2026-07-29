import React, { lazy, Suspense } from 'react';
import { AppPlugin } from '@grafana/data';
import { initPluginTranslations } from '@grafana/i18n';
import { loadResources } from '@grafana/scenes';
import { LoadingPlaceholder } from '@grafana/ui';

import pluginJson from './plugin.json';

await initPluginTranslations(pluginJson.id, [loadResources]);

const LazyApp = lazy(() => import('./components/App'));

const App = () => (
  <Suspense fallback={<LoadingPlaceholder text="Loading BioETL workspaces…" />}>
    <LazyApp />
  </Suspense>
);

export const plugin = new AppPlugin().setRootPage(App);
