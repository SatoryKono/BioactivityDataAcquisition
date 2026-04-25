# Testing Support Migration Plan (2026-04-25)

## Objective

Migrate root-level `testing_support/` into `tests/testing_support/` without breaking tests, quality gates, or repository structure governance.

## Current State

- Root package exists:
  - `testing_support/__init__.py`
  - `testing_support/bronze_writer.py`
  - `testing_support/neo4j_memory_sync.py`
- Tests import from `testing_support.*`.
- Governance allows root-level `testing_support` and references it in:
  - `configs/quality/repo_structure_catalog.yaml`
  - `docs/00-project/governance/03-file-policy.md`
  - `tests/unit/scripts/repo/test_audit_root_cleanliness.py`

## Target State

- Shared test helpers live under `tests/testing_support/`.
- Test imports use `tests.testing_support.*`.
- Root-level `testing_support/` removed.
- Governance rules and structure-audit tests updated to the new location.

## Constraints and Assumptions

- Migration should not change runtime (`src/bioetl`) behavior.
- Only test support and governance surfaces are in scope.
- Rollout should minimize CI breakage and ease rollback.

## Migration Strategy

Use two-step delivery for safety:

1. PR-1: Move + compatibility shim + import migration.
2. PR-2: Remove shim + finalize governance cleanup.

This reduces risk and keeps each PR easy to review and revert.

## Detailed Steps

### Phase 1: Baseline and Branch Setup

1. Create branch:
   - `git checkout -b chore/migrate-testing-support`
2. Capture references:
   - `rg -n "testing_support" .`
3. Record baseline checks:
   - `uv run ruff check src tests`
   - `PYTHONPYCACHEPREFIX=/tmp/pycache .venv/bin/pytest tests/unit/scripts/repo/test_audit_root_cleanliness.py -q`

Exit criteria:
- Baseline status captured before edits.

### Phase 2: Introduce New Package Location

1. Create package:
   - `tests/testing_support/__init__.py`
2. Copy/move support modules:
   - `testing_support/bronze_writer.py` -> `tests/testing_support/bronze_writer.py`
   - `testing_support/neo4j_memory_sync.py` -> `tests/testing_support/neo4j_memory_sync.py`

Exit criteria:
- New package imports cleanly in test environment.

### Phase 3: Compatibility Layer (PR-1)

Keep root-level `testing_support` as temporary shim:

- `testing_support/bronze_writer.py` re-exports from `tests.testing_support.bronze_writer`
- `testing_support/neo4j_memory_sync.py` re-exports from `tests.testing_support.neo4j_memory_sync`

Purpose:
- Preserve compatibility while import migration lands.

Exit criteria:
- Both old and new import paths resolve.

### Phase 4: Update Test Imports

1. Replace imports in tests:
   - `from testing_support...` -> `from tests.testing_support...`
2. Verify no stale usage:
   - `rg -n "from testing_support\\.|import testing_support\\." tests`

Exit criteria:
- No test files import root-level `testing_support`.

### Phase 5: Governance and Policy Updates

Update all policy surfaces to the new canonical location:

1. `configs/quality/repo_structure_catalog.yaml`
   - move approved root-level test support entry to reflect `tests/testing_support` policy.
2. `docs/00-project/governance/03-file-policy.md`
   - update wording from root-level allowance to test-tree allowance.
3. `tests/unit/scripts/repo/test_audit_root_cleanliness.py`
   - update assertions for approved roots accordingly.
4. If needed, update `.github/root-allowlist.txt` references.

Exit criteria:
- Structure/audit policy is consistent with new path.

### Phase 6: Remove Shim (PR-2)

After Phase 5 is merged and stable:

1. Delete root-level `testing_support/`.
2. Re-run repo-wide reference search:
   - `rg -n "testing_support" .`

Exit criteria:
- No active dependency on root-level package remains.

## Validation Matrix

Run after PR-1 and PR-2:

1. Lint and imports:
   - `uv run ruff check src tests`
2. Focused test suites using migrated helpers:
   - `PYTHONPYCACHEPREFIX=/tmp/pycache .venv/bin/pytest tests/unit/infrastructure/storage/bronze_writer -q`
   - `PYTHONPYCACHEPREFIX=/tmp/pycache .venv/bin/pytest tests/unit/scripts/ops/neo4j_memory_sync -q`
3. Structure governance:
   - `PYTHONPYCACHEPREFIX=/tmp/pycache .venv/bin/pytest tests/unit/scripts/repo/test_audit_root_cleanliness.py -q`
4. Optional full architecture/quality gate used by CI.

## Risks and Mitigations

1. Import path regressions.
   - Mitigation: temporary shim in PR-1.
2. Governance mismatch (policy vs filesystem).
   - Mitigation: update catalog, docs, and audit tests in same migration window.
3. Hidden references outside tests.
   - Mitigation: global `rg` search before and after shim removal.
4. Large diff review complexity.
   - Mitigation: two PRs with clear boundaries.

## Rollback Plan

If regressions occur:

1. Revert PR-2 (shim removal) first.
2. If needed, revert PR-1 and keep root-level package.
3. Re-run baseline checks to confirm recovery.

## Deliverables

1. PR-1:
   - new `tests/testing_support/*`
   - migrated test imports
   - temporary root-level shim
2. PR-2:
   - root-level `testing_support/` removed
   - governance and audit surfaces finalized
   - all checks green

