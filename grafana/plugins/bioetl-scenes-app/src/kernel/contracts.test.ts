import {
  dashboardUrl,
  dashboardTimeRangeUrl,
  EMPTY_STATES,
  parseRouteContext,
  RouteContext,
  serializeRouteContext,
} from './contracts';

describe('route context contract', () => {
  const context: RouteContext = {
    workflow: 'chembl',
    pipeline: 'chembl_activity',
    from: 'now-6h',
    to: 'now',
    timezone: 'UTC',
    runType: 'incremental',
    runId: 'run-42',
    provider: 'chembl',
    stage: 'transform',
    reason: 'dq',
    basis: 'RUN',
    origin: 'operations-home',
  };

  it('round-trips every allow-listed field', () => {
    expect(parseRouteContext(serializeRouteContext(context))).toEqual(context);
  });

  it('drops unknown query fields', () => {
    expect(parseRouteContext('var-pipeline=x&payload_hash=secret')).toEqual({
      pipeline: 'x',
    });
  });

  it('preserves context in JSON fallback links', () => {
    const url = dashboardUrl('bioetl-runtime', context);
    expect(url).toContain('/d/bioetl-runtime?');
    expect(url).toContain('var-run_id=run-42');
    expect(url).toContain('origin=operations-home');
  });

  it('keeps interpolated time range fields out of the fallback dashboard path', () => {
    const href = dashboardTimeRangeUrl('bioetl-overview-v2').replace(
      '${__url_time_range}', 'from=now-12h&to=now&timezone=browser'
    );
    const url = new URL(href, 'http://127.0.0.1:3001');
    expect(url.pathname).toBe('/d/bioetl-overview-v2');
    expect(url.searchParams.get('from')).toBe('now-12h');
    expect(url.searchParams.get('to')).toBe('now');
    expect(url.searchParams.get('timezone')).toBe('browser');
  });

  it('keeps the complete typed empty-state ontology', () => {
    expect(EMPTY_STATES).toHaveLength(8);
    expect(EMPTY_STATES).toContain('VALID_EMPTY');
    expect(EMPTY_STATES).toContain('BACKEND_ERROR');
  });
});
