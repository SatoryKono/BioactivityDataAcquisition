import { RouteSlug } from '../constants';
import routeContract from './routes.json';

export type KernelComponent =
  | 'Context Bar'
  | 'Verdict Strip'
  | 'Evidence Confidence'
  | 'Status Matrix'
  | 'Alert List'
  | 'Action Rail'
  | 'Empty State'
  | 'Event Timeline';

export interface WorkspaceRoute {
  slug: RouteSlug;
  title: string;
  subtitle: string;
  dominantLocalization: string;
  decisionObjects: readonly KernelComponent[];
  compatibilityUids: readonly string[];
  primaryPanelIds: readonly number[];
}

export const WORKSPACE_ROUTES = routeContract.routes as readonly WorkspaceRoute[];

export function routeBySlug(slug: RouteSlug): WorkspaceRoute {
  const route = WORKSPACE_ROUTES.find((candidate) => candidate.slug === slug);
  if (route === undefined) {
    throw new Error(`Unknown workspace route: ${slug}`);
  }
  return route;
}
