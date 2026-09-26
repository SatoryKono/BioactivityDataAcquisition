export interface SelectorShellOptions {
  selectorContextPath: string;
  autoApplyExactRunContext: boolean;
  autoApplyLastRunDefaults: boolean;
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
  run_status?: string;
  provider?: string;
  started_at?: string;
}

export interface SelectorDefaultsPolicy {
  policy?: string;
  run_type_fallback?: string;
  overview_landing?: string;
  run_id_list_order?: string;
  url_var_precedence?: string;
  non_overview_native_run_type_default?: string;
}

export interface SelectorContextPayload {
  contract: string;
  resolved_via: string;
  selected: ResolvedSelectorState;
  options?: Record<string, string[]>;
  defaults?: SelectorDefaultsPolicy;
}

export const defaultOptions: SelectorShellOptions = {
  selectorContextPath: '/ops/control-plane/selector-context',
  autoApplyExactRunContext: true,
  autoApplyLastRunDefaults: true,
  showDebugDetails: false,
};
