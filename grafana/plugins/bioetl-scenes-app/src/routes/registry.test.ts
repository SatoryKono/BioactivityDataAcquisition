import { ROUTE_SLUGS } from '../constants';
import { WORKSPACE_ROUTES } from './registry';

describe('workspace route registry', () => {
  it('defines exactly six unique routes', () => {
    expect(WORKSPACE_ROUTES.map((route) => route.slug)).toEqual(ROUTE_SLUGS);
  });

  it('keeps first-screen decision objects bounded', () => {
    for (const route of WORKSPACE_ROUTES) {
      expect(route.decisionObjects.length).toBeLessThanOrEqual(5);
      expect(route.dominantLocalization).not.toBe('');
      expect(route.compatibilityUids.length).toBeGreaterThan(0);
    }
  });

  it('keeps Trust and DQ as separate compatibility UIDs', () => {
    const route = WORKSPACE_ROUTES.find((candidate) => candidate.slug === 'data-trust-recovery');
    expect(route?.compatibilityUids).toEqual(['bioetl-control-plane-v1', 'bioetl-dq-v2']);
  });
  it('maps the six routes only to the five approved current JSON UIDs', () => {
    const uids = [...new Set(WORKSPACE_ROUTES.flatMap((route) => [...route.compatibilityUids]))].sort();
    expect(uids).toEqual([
      'bioetl-control-plane-v1',
      'bioetl-dq-v2',
      'bioetl-incident-v1',
      'bioetl-overview-v2',
      'bioetl-run-explorer-v1',
    ]);
  });
});
