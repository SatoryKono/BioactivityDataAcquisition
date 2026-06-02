import { SelectorContextPayload, VisibleSelectorState } from './types';

export const NO_SELECTION_RUN_ID = '-';
export const ALL_SCOPE = 'All';

export interface NextShellUpdate {
  'var-workflow': string;
  'var-pipeline': string;
  'var-run_type': string;
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

export function buildSelectorContextUrl(basePath: string, runId: string): string {
  const query = new URLSearchParams({ run_id: runId });
  return `${basePath}?${query.toString()}`;
}

export function buildNextShellUpdate(
  current: VisibleSelectorState,
  payload: SelectorContextPayload
): NextShellUpdate | null {
  if (payload.resolved_via !== 'selected_run_id') {
    return null;
  }

  const nextWorkflow = normalizeVariableText(payload.selected.workflow);
  const nextPipeline = normalizeVariableText(payload.selected.pipeline);
  const nextRunType = normalizeVariableText(payload.selected.run_type);

  if (nextWorkflow === '' || nextPipeline === '' || nextRunType === '') {
    return null;
  }

  const currentWorkflow = normalizeVariableText(current.workflow);
  const currentPipeline = normalizeVariableText(current.pipeline);
  const currentRunType = normalizeVariableText(current.runType);

  if (
    currentWorkflow === nextWorkflow &&
    currentPipeline === nextPipeline &&
    currentRunType === nextRunType
  ) {
    return null;
  }

  return {
    'var-workflow': nextWorkflow,
    'var-pipeline': nextPipeline,
    'var-run_type': nextRunType,
  };
}

export function summarizeSyncState(
  current: VisibleSelectorState,
  payload: SelectorContextPayload | null
): string {
  if (!hasExactRunSelection(current.runId)) {
    return 'Idle: no exact Run ID selected.';
  }
  if (payload == null) {
    return `Resolving exact run ${current.runId}...`;
  }
  if (payload.resolved_via !== 'selected_run_id') {
    return `Exact run ${current.runId} did not resolve authoritative selector context.`;
  }
  const selected = payload.selected;
  return `Resolved ${selected.run_id}: workflow=${selected.workflow}, pipeline=${selected.pipeline}, run_type=${selected.run_type}.`;
}
