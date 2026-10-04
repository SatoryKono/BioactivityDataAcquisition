import {
  EmbeddedScene,
  PanelBuilders,
  SceneControlsSpacer,
  SceneFlexItem,
  SceneFlexLayout,
  SceneTimePicker,
  SceneTimeRange,
} from '@grafana/scenes';
import { locationService } from '@grafana/runtime';

import { WorkspaceRoute } from '../routes/registry';
import { dashboardUrl, parseRouteContext } from './contracts';

function fallbackLinks(route: WorkspaceRoute, query: string): string {
  const context = parseRouteContext(query);
  return route.compatibilityUids
    .map(
      (uid) =>
        `<a href="${dashboardUrl(uid, context).replaceAll('&', '&amp;')}" style="margin-right:12px">Open JSON: ${uid}</a>`
    )
    .join('');
}

export function buildWorkspaceScene(route: WorkspaceRoute): EmbeddedScene {
  const componentList = route.decisionObjects.map((component) => `<li>${component}</li>`).join('');
  const content = (query: string) => [
    `<div data-bioetl-route="${route.slug}" style="max-width:100%;overflow-x:hidden">`,
    `<h2>${route.title}</h2><p>${route.subtitle}</p>`,
    `<p><strong>Localization:</strong> ${route.dominantLocalization}</p>`,
    `<ol>${componentList}</ol>`,
    `<p>${fallbackLinks(route, query)}</p>`,
    '<p><small>Shadow route · read-only · JSON remains authoritative fallback.</small></p>',
    '</div>',
  ].join('');

  const panel = PanelBuilders.text()
    .setTitle(`${route.title} · decision surface`)
    .setOption('mode', 'html' as never)
    .setOption('content', content(locationService.getLocation().search))
    .build();
  const scene = new EmbeddedScene({
    $timeRange: new SceneTimeRange({ from: 'now-12h', to: 'now' }),
    body: new SceneFlexLayout({
      direction: 'column',
      children: [
        new SceneFlexItem({
          minHeight: 360,
          body: panel,
        }),
      ],
    }),
    controls: [new SceneControlsSpacer(), new SceneTimePicker({ isOnCanvas: true })],
  });
  scene.addActivationHandler(() => {
    const refreshLinks = (query: string) => {
      panel.setState({ options: { ...panel.state.options, content: content(query) } });
    };
    const subscription = locationService.getLocationObservable().subscribe((location) => {
      refreshLinks(location.search);
    });
    // Native Back/Forward can precede the host's location-service notification.
    const onPopState = () => refreshLinks(window.location.search);
    window.addEventListener('popstate', onPopState);
    return () => {
      subscription.unsubscribe();
      window.removeEventListener('popstate', onPopState);
    };
  });
  return scene;
}
