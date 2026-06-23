---
title: "[TEST-AUDIT] Trim legacy root observability test surface and replace weak assertions"
github_issue: 5423
labels: enhancement, observability, technical-debt
assignees: []
---

## Context

The test-system audit confirmed that the root observability unit file still
contains weak "no exception means success" assertions while the specialized
`tests/unit/infrastructure/observability/` subtree already provides stronger
postcondition-based coverage.

## Problem

- `tests/unit/infrastructure/test_observability.py` still contains metrics tests
  that do not assert observable state changes.
- The same behavior is covered more rigorously in the specialized observability
  test subtree.
- The root file also overlaps with anomaly detection coverage, so deleting it
  wholesale would be too coarse.

## Evidence

- `tests/unit/infrastructure/test_observability.py`
- `tests/unit/infrastructure/observability/test_metrics.py`
- `tests/unit/infrastructure/observability/test_anomaly.py`
- `tests/unit/infrastructure/observability/test_prometheus_metrics.py`

## Proposed Solution

1. Split the root file into:
   - unique coverage worth retaining
   - duplicate/weak metrics smoke tests to delete or rewrite
2. Replace weak assertions with explicit before/after counter or state checks.
3. Keep anomaly coverage only where it remains unique after comparison with the
   specialized observability subtree.

## Acceptance Criteria

- [ ] No observability test relies on "no exception means success"
- [ ] Duplicate metrics-smoke coverage is removed or rewritten as
      postcondition-based checks
- [ ] Remaining root-level observability tests are unique and justified
- [ ] Specialized observability subtree stays green

## Validation

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/pytest \
  tests/unit/infrastructure/test_observability.py \
  tests/unit/infrastructure/observability/ \
  -p no:xdist -q
```

## Risks

- Over-aggressive deletion could drop unique anomaly coverage.
- Rewrites must preserve the current observability contract shape.
