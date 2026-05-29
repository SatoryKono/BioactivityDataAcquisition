# Drive BioETL technical debt to zero

**Status**: proposed
**Priority**: P0
**Labels**: `architecture`, `tech-debt`, `governance`, `epic`
**GitHub Issue**: `TBD`
**Issue State**: draft
**Last synced**: 2026-05-29

## Problem

BioETL has strong governance and currently passes the critical architecture,
determinism, idempotency, contract-registry, replay-fixture, and observability
governance suites, but residual technical debt is still concentrated in bounded
compatibility surfaces and hotspot families rather than in open architectural
breakage.

Confirmed residual debt from the 2026-05-29 audit:

- `14` retained sanctioned public entrypoints remain governed as stable burden:
  `configs/quality/compatibility_facade_inventory.yaml`
- `37` public/private twin-module pairs remain in the live importer census:
  `reports/quality/compatibility-importer-census.md`
- duplication hotspot baselines remain non-zero in:
  - `src/bioetl/application/services/control_plane/` (`15` duplicate clusters)
  - `src/bioetl/composition/runtime_builders/` (`11` duplicate clusters)
  - `src/bioetl/composition/bootstrap/runtime/` (`5` duplicate clusters)
- `63` repo-wide zero-import candidates remain triaged but not fully removed:
  `reports/quality/dead-code-inventory.md`
- compatibility test debt budget remains explicitly non-zero:
  `configs/quality/test_governance_audit.yaml`
- one observability compatibility alias emitter remains in runtime evidence:
  `reports/observability/runtime_cardinality_inventory.json`

This issue is the umbrella epic to close the remaining debt budgets rather than
only tracking them.

## Goal

Reduce tracked technical debt to zero by removing or collapsing the remaining
compatibility wrappers, eliminating duplicate hotspot clusters, retiring
unneeded zero-import modules, and converting residual report-only governance
into fail-fast CI enforcement.

Zero means:

- no transition compatibility debt
- no removable zero-import compatibility wrappers left in first-party source
- no residual twin-module private imports outside explicitly sanctioned owner
  seams
- no duplicate-cluster budgets in the tracked hotspot families
- no compatibility-test retirement budget left open
- no observability compatibility alias emitters left in runtime evidence

Stable public API that is intentionally retained for external consumers is not
counted as debt once its first-party usage is narrowed and its governance stays
bounded.

## Scope

### 1. Compatibility collapse

- Burn down retained compatibility wrappers under:
  - `src/bioetl/application/services/control_plane/`
  - `src/bioetl/composition/`
  - `src/bioetl/infrastructure/config/`
  - `src/bioetl/domain/`
- Collapse public/private twin families tracked by:
  - `configs/quality/compatibility_twin_module_ratchet.yaml`
  - `reports/quality/compatibility-importer-census.md`

### 2. Dead code removal

- Convert triaged `retain_compat_shim` and other zero-import candidates in
  `reports/quality/dead-code-inventory.md` into one of:
  - removed
  - promoted to stable public API with zero first-party debt burden
  - explicitly kept with fresh owner rationale and no remaining debt budget

### 3. Duplication burn-down

- Drive duplicate-cluster baselines to zero in:
  - `src/bioetl/application/services/control_plane/`
  - `src/bioetl/composition/runtime_builders/`
  - `src/bioetl/composition/bootstrap/runtime/`
- Keep `src/bioetl/application/core/` on a downward path after the current
  bounded-growth baseline.

### 4. Runtime / CLI / bootstrap consolidation

- Keep `bootstrap/{assembly,cli,runtime}` split intact.
- Remove residual helper duplication and compatibility-only forwarding around
  runtime/bootstrap builders instead of re-merging layers.

### 5. Test / observability governance closeout

- Reduce `compatibility_test_file_max` in
  `configs/quality/test_governance_audit.yaml` to `0`.
- Remove the compatibility alias emitter
  `checkpoint_saved_at_epoch_seconds` from
  `reports/observability/runtime_cardinality_inventory.json`.

## Non-goals

- Re-opening already green contract-registry, DQ-ref, or Bronze fixture gap
  surfaces without new evidence.
- Removing intentionally stable external public entrypoints in one step without
  an external consumer audit.
- Weakening layering, determinism, replay, or idempotency rules to make debt
  metrics look better.

## Execution plan

### Phase 1. Visibility

1. Freeze the current debt baseline in:
   - `reports/quality/dead-code-inventory.md`
   - `reports/quality/compatibility-importer-census.md`
   - `reports/quality/hotspot-duplication-baseline.{md,json}`
   - `reports/observability/runtime_cardinality_inventory.json`
2. For every retained wrapper or twin family, record one owner path, one
   canonical replacement path, and one removal condition.
3. Split debt into:
   - removable now
   - removable after caller migration
   - stable public API burden only

### Phase 2. Isolation

1. Ban new private twin-module imports in first-party source.
2. Narrow first-party imports to sanctioned public seams only.
3. Stop test growth on compatibility wrappers and root facades.
4. Isolate duplication-heavy helpers behind one canonical owner module per
   family.

### Phase 3. Removal

1. Remove zero-import compatibility wrappers from
   `src/bioetl/application/services/control_plane/`.
2. Collapse twin-module families to one canonical import path.
3. Refactor control-plane and runtime-builder duplicate clusters to zero.
4. Delete compatibility-only observability alias emission.
5. Retire compatibility-focused tests that only protect removed wrappers.

### Phase 4. Enforcement

1. Convert hotspot duplication families from reviewed baselines to zero-budget
   fail-fast gates.
2. Fail CI on new zero-import retained compatibility modules.
3. Fail CI on any new compatibility test file or compatibility alias emitter.
4. Require new public facade or lazy export additions to include:
   - owner
   - removal or permanence rationale
   - first-party caller budget
   - dedicated architecture test coverage

## Acceptance

- `reports/quality/dead-code-inventory.md` contains no removable
  `retain_compat_shim` rows.
- `reports/quality/compatibility-importer-census.md` shows:
  - `tracked_twin_family_count: 0` or explicitly permanent families only with
    `0` private first-party debt outside owner seams
  - no debt-classified retained wrappers without live rationale
- `reports/quality/hotspot-duplication-baseline.json` shows `0` duplicate
  clusters for:
  - `application_services_control_plane`
  - `composition_runtime_builders`
  - `composition_bootstrap_runtime`
- `configs/quality/test_governance_audit.yaml` ratchets
  `compatibility_test_file_max` to `0`
- `reports/observability/runtime_cardinality_inventory.json` has no
  compatibility alias emitters
- `configs/quality/debt_scorecard.yaml` no longer tracks non-zero budgets for
  these residual debt families
- targeted verification stays green:
  - `tests/architecture/test_compatibility_*`
  - `tests/architecture/test_bootstrap_layer_boundaries.py`
  - `tests/architecture/test_determinism_identity_policy.py`
  - `tests/architecture/test_pipeline_config_idempotency_contract.py`
  - `tests/architecture/test_observability_metric_governance.py`
  - `tests/architecture/test_quality_debt_scorecard.py`

## Suggested issue breakdown

- Follow or reopen caller-narrowing work related to stable public entrypoints:
  `#4575`
- Follow or reopen duplication hotspot closeout:
  `#4547`, `#4548`, `#4552`, `#4554`
- Follow or reopen sanctioned twin-family collapse:
  `#4744`
- Follow or reopen oversized-source split-on-touch work:
  `#4679`
- Follow or reopen zero-import retained module burn-down from the prior
  technical-debt issue wave

## Evidence

- `docs/02-architecture/generated/module-dependency-map.json`
- `configs/quality/compatibility_facade_inventory.yaml`
- `configs/quality/compatibility_twin_module_ratchet.yaml`
- `configs/quality/debt_scorecard.yaml`
- `configs/quality/test_governance_audit.yaml`
- `reports/quality/compatibility-importer-census.md`
- `reports/quality/dead-code-inventory.md`
- `reports/quality/hotspot-duplication-baseline.md`
- `reports/observability/runtime_cardinality_inventory.json`

## Risks

- Some retained public seams may still have out-of-repo consumers. Removal must
  be gated by an explicit external-caller audit.
- Refactoring hotspot families without preserving replay/control-plane tests can
  hide determinism regressions.
- Aggressive wrapper deletion can create patch-target churn in tests unless the
  canonical owner paths are stabilized first.
