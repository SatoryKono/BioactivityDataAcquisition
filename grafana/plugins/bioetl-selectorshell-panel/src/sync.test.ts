import { buildNextShellUpdate, buildSelectorContextUrl, hasExactRunSelection } from './sync';
import { SelectorContextPayload, VisibleSelectorState } from './types';

function buildPayload(overrides: Partial<SelectorContextPayload['selected']> = {}): SelectorContextPayload {
  return {
    contract: 'control_plane_selector_context_v1',
    resolved_via: 'selected_run_id',
    selected: {
      workflow: 'chembl_target',
      pipeline: 'chembl_target',
      run_type: 'backfill',
      run_id: 'run-123',
      ...overrides,
    },
  };
}

describe('selector shell sync helpers', () => {
  it('detects exact run selection', () => {
    expect(hasExactRunSelection('-')).toBe(false);
    expect(hasExactRunSelection('')).toBe(false);
    expect(hasExactRunSelection('run-123')).toBe(true);
  });

  it('builds selector-context URL', () => {
    expect(buildSelectorContextUrl('/ops/control-plane/selector-context', 'run-123')).toBe(
      '/ops/control-plane/selector-context?run_id=run-123'
    );
  });

  it('returns null when current shell already matches exact run context', () => {
    const current: VisibleSelectorState = {
      workflow: 'chembl_target',
      pipeline: 'chembl_target',
      runType: 'backfill',
      runId: 'run-123',
    };

    expect(buildNextShellUpdate(current, buildPayload())).toBeNull();
  });

  it('returns a locationService update when exact run context differs from visible selectors', () => {
    const current: VisibleSelectorState = {
      workflow: 'chembl_target',
      pipeline: 'chembl_assay',
      runType: 'incremental',
      runId: 'run-123',
    };

    expect(buildNextShellUpdate(current, buildPayload())).toEqual({
      'var-workflow': 'chembl_target',
      'var-pipeline': 'chembl_target',
      'var-run_type': 'backfill',
    });
  });

  it('does not produce updates for non exact-run payloads', () => {
    const payload = buildPayload();
    payload.resolved_via = 'latest_terminal_run_for_scope';
    const current: VisibleSelectorState = {
      workflow: 'chembl_target',
      pipeline: 'chembl_assay',
      runType: 'incremental',
      runId: 'run-123',
    };

    expect(buildNextShellUpdate(current, payload)).toBeNull();
  });
});
