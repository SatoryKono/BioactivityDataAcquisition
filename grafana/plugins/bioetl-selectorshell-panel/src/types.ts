export interface SelectorShellOptions {
  selectorContextPath: string;
  autoApplyExactRunContext: boolean;
  showDebugDetails: boolean;
}

export interface VisibleSelectorState {
  workflow: string;
  pipeline: string;
  runType: string;
  runId: string;
}

export interface ResolvedSelectorState {
  workflow: string;
  pipeline: string;
  run_type: string;
  run_id: string;
}

export interface SelectorContextPayload {
  contract: string;
  resolved_via: string;
  selected: ResolvedSelectorState;
}

export const defaultOptions: SelectorShellOptions = {
  selectorContextPath: '/ops/control-plane/selector-context',
  autoApplyExactRunContext: true,
  showDebugDetails: false,
};
