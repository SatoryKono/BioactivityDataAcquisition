import pluginJson from './plugin.json';

export const PLUGIN_BASE_URL = `/a/${pluginJson.id}`;

export const ROUTE_SLUGS = [
  'operations-home',
  'pipeline-flow',
  'dependency-health',
  'incident-console',
  'data-trust-recovery',
  'run-explorer',
] as const;

export type RouteSlug = (typeof ROUTE_SLUGS)[number];

export function prefixRoute(route: RouteSlug): string {
  return `${PLUGIN_BASE_URL}/${route}`;
}
