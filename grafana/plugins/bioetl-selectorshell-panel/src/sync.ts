import {
  SelectorContextPayload,
  VisibleSelectorState,
} from './types';

export const NO_SELECTION_RUN_ID = '-';
export const ALL_SCOPE = 'All';
export const ALL_SCOPE_TOKENS = new Set(['All', '$__all', '__all', '*']);
export const UNKNOWN_SCOPE = 'unknown';

export interface NextShellUpdate {
  'var-workflow'?: string;
  'var-pipeline'?: string;
  'var-run_type'?: string;
  'var-run_id'?: string;
}

export function normalizeVariableText(value: string | null | undefined): string {
  if (value == null) {
    return '';
  }
  return value.trim();
}

export function hasExactRunSelection(runId: string): boolean {
  const normalized = normalizeVariableText(runId);
  return normalized !== '' && normalized !== NO_SELECTION_RUN_ID;
}

export function isAggregateScope(value: string): boolean {
  const normalized = normalizeVariableText(value);
  return normalized === '' || ALL_SCOPE_TOKENS.has(normalized);
}

export function isFailClosedUnknown(value: string): boolean {
  return normalizeVariableText(value) === UNKNOWN_SCOPE;
}

/**
 * True when the visible shell looks like an unset fail-closed/native default
 * and should accept last-run defaults from selector-context.
 */
export function shouldApplyLastRunDefaults(current: VisibleSelectorState): boolean {
  if (hasExactRunSelection(current.runId)) {
    return false;
  }
  const pipelineUnset =
    isAggregateScope(current.pipeline) || isFailClosedUnknown(current.pipeline);
  const workflowAggregate = isAggregateScope(current.workflow);
  return pipelineUnset || workflowAggregate || !hasExactRunSelection(current.runId);
}

export function buildSelectorContextUrl(
  basePath: string,
  params: { runId?: string; workflow?: string; pipeline?: string; runType?: string } = {}
): string {
  const query = new URLSearchParams();
  if (params.runId && hasExactRunSelection(params.runId)) {
    query.set('run_id', params.runId);
  } else {
    if (params.workflow && !isAggregateScope(params.workflow)) {
      query.set('workflow', params.workflow);
    }
    if (params.pipeline && !isAggregateScope(params.pipeline) && !isFailClosedUnknown(params.pipeline)) {
      query.set('pipeline', params.pipeline);
    }
    if (params.runType && !isAggregateScope(params.runType)) {
      query.set('run_type', params.runType);
    }
  }
  const qs = query.toString();
  return qs ? `${basePath}?${qs}` : basePath;
}

export function buildNextShellUpdate(
  current: VisibleSelectorState,
  payload: SelectorContextPayload,
  options: { applyRunId?: boolean; allowLastRunDefaults?: boolean } = {}
): NextShellUpdate | null {
  const applyRunId = options.applyRunId ?? false;
  const allowLastRunDefaults = options.allowLastRunDefaults ?? false;

  if (payload.resolved_via === 'selected_run_id') {
    return buildExactRunShellUpdate(current, payload, applyRunId);
  }

  if (!allowLastRunDefaults) {
    return null;
  }

  if (!shouldApplyLastRunDefaults(current)) {
    return null;
  }

  if (payload.resolved_via === 'no_manifest_for_scope') {
    return buildFallbackShellUpdate(current, payload);
  }

  if (
    payload.resolved_via === 'latest_terminal_run_for_scope' ||
    payload.resolved_via === 'latest_manifest_created_at_for_scope'
  ) {
    return buildExactRunShellUpdate(current, payload, true);
  }

  return null;
}

function buildExactRunShellUpdate(
  current: VisibleSelectorState,
  payload: SelectorContextPayload,
  applyRunId: boolean
): NextShellUpdate | null {
  const nextWorkflow = normalizeVariableText(payload.selected.workflow);
  const nextPipeline = normalizeVariableText(payload.selected.pipeline);
  const nextRunType = normalizeVariableText(payload.selected.run_type);
  const nextRunId = normalizeVariableText(payload.selected.run_id);

  if (nextWorkflow === '' || nextPipeline === '' || nextRunType === '') {
    return null;
  }

  const currentWorkflow = normalizeVariableText(current.workflow);
  const currentPipeline = normalizeVariableText(current.pipeline);
  const currentRunType = normalizeVariableText(current.runType);
  const currentRunId = normalizeVariableText(current.runId);

  const update: NextShellUpdate = {};
  if (currentWorkflow !== nextWorkflow) {
    update['var-workflow'] = nextWorkflow;
  }
  if (currentPipeline !== nextPipeline) {
    update['var-pipeline'] = nextPipeline;
  }
  if (currentRunType !== nextRunType) {
    update['var-run_type'] = nextRunType;
  }
  if (applyRunId && nextRunId !== '' && currentRunId !== nextRunId) {
    update['var-run_id'] = nextRunId;
  }

  return Object.keys(update).length === 0 ? null : update;
}

function buildFallbackShellUpdate(
  current: VisibleSelectorState,
  payload: SelectorContextPayload
): NextShellUpdate | null {
  const fallback =
    normalizeVariableText(payload.defaults?.run_type_fallback) ||
    normalizeVariableText(payload.selected.run_type) ||
    'backfill';
  const currentRunType = normalizeVariableText(current.runType);
  if (currentRunType === fallback || isAggregateScope(currentRunType)) {
    if (currentRunType === fallback) {
      return null;
    }
    return { 'var-run_type': fallback };
  }
  return null;
}

export function summarizeSyncState(
  current: VisibleSelectorState,
  payload: SelectorContextPayload | null
): string {
  if (payload == null) {
    if (hasExactRunSelection(current.runId)) {
      return `Resolving exact run ${current.runId}...`;
    }
    return 'Resolving last-run selector defaults...';
  }
  if (payload.resolved_via === 'selected_run_id') {
    const selected = payload.selected;
    return `Resolved ${selected.run_id}: workflow=${selected.workflow}, pipeline=${selected.pipeline}, run_type=${selected.run_type}.`;
  }
  if (
    payload.resolved_via === 'latest_terminal_run_for_scope' ||
    payload.resolved_via === 'latest_manifest_created_at_for_scope'
  ) {
    const selected = payload.selected;
    return `Last-run defaults: ${selected.run_id} workflow=${selected.workflow} pipeline=${selected.pipeline} run_type=${selected.run_type}.`;
  }
  if (payload.resolved_via === 'no_manifest_for_scope') {
    return `No catalog run for scope; run_type fallback=${payload.defaults?.run_type_fallback ?? 'backfill'}.`;
  }
  return `Selector context resolved_via=${payload.resolved_via}.`;
}
