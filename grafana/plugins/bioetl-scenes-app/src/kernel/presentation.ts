import {
  EmbeddedScene,
  PanelBuilders,
  SceneControlsSpacer,
  SceneFlexItem,
  SceneFlexLayout,
  SceneTimePicker,
  SceneTimeRange,
} from '@grafana/scenes';

import { WorkspaceRoute } from '../routes/registry';

function fallbackLinks(route: WorkspaceRoute): string {
  return route.compatibilityUids
    .map(
      (uid) =>
        `<a href="/d/${uid}\${__url_time_range}" style="margin-right:12px">Open JSON: ${uid}</a>`
    )
    .join('');
}

export function buildWorkspaceScene(route: WorkspaceRoute): EmbeddedScene {
  const componentList = route.decisionObjects.map((component) => `<li>${component}</li>`).join('');
  const content = [
    `<div data-bioetl-route="${route.slug}" style="max-width:100%;overflow-x:hidden">`,
    `<h2>${route.title}</h2><p>${route.subtitle}</p>`,
    `<p><strong>Localization:</strong> ${route.dominantLocalization}</p>`,
    `<ol>${componentList}</ol>`,
    `<p>${fallbackLinks(route)}</p>`,
    '<p><small>Shadow route · read-only · JSON remains authoritative fallback.</small></p>',
    '</div>',
  ].join('');

  return new EmbeddedScene({
    $timeRange: new SceneTimeRange({ from: 'now-12h', to: 'now' }),
    body: new SceneFlexLayout({
      direction: 'column',
      children: [
        new SceneFlexItem({
          minHeight: 360,
          body: PanelBuilders.text()
            .setTitle(`${route.title} · decision surface`)
            .setOption('mode', 'html' as never)
            .setOption('content', content)
            .build(),
        }),
      ],
    }),
    controls: [new SceneControlsSpacer(), new SceneTimePicker({ isOnCanvas: true })],
  });
}
