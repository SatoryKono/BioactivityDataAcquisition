---
title: "[TEST-AUDIT] Add integration coverage for cleanup and postrun compaction semantics"
github_issue: 5432
labels: enhancement, integration-tests, technical-debt
assignees: []
---

## Context

E2E intentionally patches out Bronze cleanup and postrun Silver compaction so
the suite remains deterministic and avoids Delta-maintenance hangs. That is a
reasonable trade-off, but the skipped runtime semantics still need narrow,
explicit coverage elsewhere.

## Problem

- Cleanup and compaction semantics are not represented in the canonical E2E path.
- Without targeted integration contracts, maintenance behavior can drift
  silently while E2E stays green.
- The current carve-out is justified, but it creates a fidelity gap.

## Evidence

- `tests/e2e/conftest.py`
- `tests/integration/infrastructure/**`
- `tests/integration/ci/**`

## Proposed Solution

1. Add narrow integration tests for:
   - Bronze retention cleanup decision surface
   - postrun compaction decision/result surface
   - any related checkpoint/control-plane interactions that determine whether
     maintenance is skipped or applied
2. Keep these tests isolated from the heavy E2E lane.
3. Reference them from the E2E carve-out docs.

## Acceptance Criteria

- [ ] Cleanup retention semantics are covered by dedicated integration tests
- [ ] Postrun compaction semantics are covered by dedicated integration tests
- [ ] E2E continues to skip maintenance paths by design
- [ ] The fidelity gap is documented and explicitly closed by the new tests

## Validation

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/pytest \
  tests/integration/infrastructure/ -p no:xdist -q
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/pytest \
  tests/integration/ci/ -p no:xdist -q
```

## Risks

- Maintenance-path tests can become timing-sensitive if they depend on heavy
  Delta behavior instead of decision-level seams.
