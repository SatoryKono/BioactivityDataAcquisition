export const EMPTY_STATES = [
  'VALID_EMPTY',
  'N/A',
  'NOT_STARTED',
  'MISSING',
  'STALE',
  'BACKEND_ERROR',
  'INCOMPLETE',
  'UNKNOWN',
] as const;

export type EmptyState = (typeof EMPTY_STATES)[number];

export const EVIDENCE_BASES = ['NOW', 'RANGE', 'RUN', 'WORKFLOW', 'GLOBAL'] as const;
export type EvidenceBasis = (typeof EVIDENCE_BASES)[number];

export interface RouteContext {
  workflow?: string;
  pipeline?: string;
  from?: string;
  to?: string;
  runType?: string;
  runId?: string;
  provider?: string;
  stage?: string;
  reason?: string;
  basis?: EvidenceBasis;
  origin?: string;
}

const CONTEXT_KEYS: ReadonlyArray<keyof RouteContext> = [
  'workflow',
  'pipeline',
  'from',
  'to',
  'runType',
  'runId',
  'provider',
  'stage',
  'reason',
  'basis',
  'origin',
];

const QUERY_KEYS: Record<keyof RouteContext, string> = {
  workflow: 'var-workflow',
  pipeline: 'var-pipeline',
  from: 'from',
  to: 'to',
  runType: 'var-run_type',
  runId: 'var-run_id',
  provider: 'var-provider',
  stage: 'var-stage',
  reason: 'var-reason',
  basis: 'basis',
  origin: 'origin',
};

export function serializeRouteContext(context: RouteContext): string {
  const params = new URLSearchParams();
  for (const key of CONTEXT_KEYS) {
    const value = context[key];
    if (value !== undefined && value !== '') {
      params.set(QUERY_KEYS[key], value);
    }
  }
  return params.toString();
}

export function parseRouteContext(query: string): RouteContext {
  const params = new URLSearchParams(query.startsWith('?') ? query.slice(1) : query);
  const context: RouteContext = {};
  for (const key of CONTEXT_KEYS) {
    const value = params.get(QUERY_KEYS[key]);
    if (value !== null && value !== '') {
      context[key] = value as never;
    }
  }
  return context;
}

export function dashboardUrl(uid: string, context: RouteContext): string {
  const suffix = serializeRouteContext(context);
  return `/d/${uid}?${suffix}`;
}
