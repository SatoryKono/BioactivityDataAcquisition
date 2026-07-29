import React from 'react';
import { SceneApp, SceneAppPage, useSceneApp } from '@grafana/scenes';

import { prefixRoute } from '../constants';
import { buildWorkspaceScene } from '../kernel/presentation';
import { WORKSPACE_ROUTES } from '../routes/registry';

export function buildSceneApp(): SceneApp {
  return new SceneApp({
    pages: WORKSPACE_ROUTES.map(
      (route) =>
        new SceneAppPage({
          title: route.title,
          subTitle: route.subtitle,
          url: prefixRoute(route.slug),
          routePath: route.slug,
          preserveUrlKeys: [
            'from',
            'to',
            'var-workflow',
            'var-pipeline',
            'var-run_type',
            'var-run_id',
            'var-provider',
            'var-stage',
            'var-reason',
            'basis',
            'origin',
          ],
          getScene: () => buildWorkspaceScene(route),
        })
    ),
    urlSyncOptions: {
      updateUrlOnInit: true,
      createBrowserHistorySteps: true,
    },
  });
}

export default function App() {
  const scene = useSceneApp(buildSceneApp);
  return <scene.Component model={scene} />;
}
