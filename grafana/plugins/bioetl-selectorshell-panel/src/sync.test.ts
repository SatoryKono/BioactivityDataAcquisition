import {
  buildNextShellUpdate,
  buildSelectorContextUrl,
  hasExactRunSelection,
  shouldApplyLastRunDefaults,
} from './sync';
import { SelectorContextPayload, VisibleSelectorState } from './types';

function buildPayload(
  overrides: Partial<SelectorContextPayload['selected']> = {},
  resolvedVia = 'selected_run_id'
): SelectorContextPayload {
  return {
    contract: 'control_plane_selector_context_v1',
    resolved_via: resolvedVia,
    selected: {
      workflow: 'chembl_target',
      pipeline: 'chembl_target',
      run_type: 'backfill',
      run_id: 'run-123',
      ...overrides,
    },
    defaults: {
      policy: 'last_run_truthful',
      run_type_fallback: 'backfill',
    },
  };
}

describe('selector shell sync helpers', () => {
  it('detects exact run selection', () => {
    expect(hasExactRunSelection('-')).toBe(false);
    expect(hasExactRunSelection('')).toBe(false);
    expect(hasExactRunSelection('run-123')).toBe(true);
  });

  it('builds selector-context URL for exact run', () => {
    expect(buildSelectorContextUrl('/ops/control-plane/selector-context', { runId: 'run-123' })).toBe(
      '/ops/control-plane/selector-context?run_id=run-123'
    );
  });

  it('builds selector-context URL for scoped last-run lookup', () => {
    expect(
      buildSelectorContextUrl('/ops/control-plane/selector-context', {
        workflow: 'chembl_target',
        pipeline: 'chembl_target',
        runType: 'backfill',
      })
    ).toBe(
      '/ops/control-plane/selector-context?workflow=chembl_target&pipeline=chembl_target&run_type=backfill'
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
      'var-pipeline': 'chembl_target',
      'var-run_type': 'backfill',
    });
  });

  it('applies last-run defaults when shell is unset', () => {
    const current: VisibleSelectorState = {
      workflow: 'All',
      pipeline: 'unknown',
      runType: 'backfill',
      runId: '-',
    };
    const payload = buildPayload({}, 'latest_terminal_run_for_scope');
    expect(shouldApplyLastRunDefaults(current)).toBe(true);
    expect(buildNextShellUpdate(current, payload, { allowLastRunDefaults: true })).toEqual({
      'var-workflow': 'chembl_target',
      'var-pipeline': 'chembl_target',
      'var-run_id': 'run-123',
    });
  });

  it('does not apply last-run defaults when allow flag is off', () => {
    const current: VisibleSelectorState = {
      workflow: 'All',
      pipeline: 'unknown',
      runType: 'All',
      runId: '-',
    };
    const payload = buildPayload({}, 'latest_terminal_run_for_scope');
    expect(buildNextShellUpdate(current, payload, { allowLastRunDefaults: false })).toBeNull();
  });

  it('falls back to backfill when catalog is empty', () => {
    const current: VisibleSelectorState = {
      workflow: 'All',
      pipeline: 'unknown',
      runType: 'All',
      runId: '-',
    };
    const payload = buildPayload(
      {
        workflow: 'All',
        pipeline: 'unknown',
        run_type: 'backfill',
        run_id: '-',
      },
      'no_manifest_for_scope'
    );
    expect(buildNextShellUpdate(current, payload, { allowLastRunDefaults: true })).toEqual({
      'var-run_type': 'backfill',
    });
  });
});
