---
title: "[TEST-AUDIT-018] E2E PR smoke vs nightly full matrix split"
labels: ci, e2e, P1
assignees: []
github_issue: 5930
---

## Context

The `2026-07-03` test-system audit identified E2E as a high-cost lane (27 files,
Delta write paths, mixed Windows path normalization) while PR feedback time is
already stressed by architecture governance scanners.

## Problem

The current workflow runs a broad e2e surface on PR paths. Full entity/provider
combinations, Delta write sign-off, and Windows path edge cases are expensive and
have shown fragility (silver/gold absolute path normalization, timeout risk).

Without an explicit PR smoke vs nightly full matrix split, teams either skip
local e2e runs or accept long PR CI cycles.

## Evidence

- `tests/e2e/` (27 files)
- `tests/e2e/conftest.py` (Local-Only, VCR, checkpoint harness)
- `configs/quality/test_matrix.yaml` (`e2e` suite and entity ownership rows)
- `.github/workflows/tests.yml`
- `reports/quality/test-governance-current.json`
- Recent path-contract fixes: `tests/architecture/test_medallion_invariants.py`, `tests/architecture/test_path_contracts.py`

## Acceptance Criteria

- [ ] PR CI runs a documented e2e smoke subset (import/bootstrap + one representative entity path).
- [ ] Nightly (or `workflow_dispatch`) runs the full e2e matrix per `test_matrix.yaml` entity rows.
- [ ] `test_matrix.yaml` and workflow docs state which markers/suites belong to smoke vs full.
- [ ] Smoke subset still covers Local-Only bootstrap, VCR replay, and medallion write path sanity.
- [ ] Full nightly matrix remains merge-blocking for release branches or via required check policy.
- [ ] No architecture invariant is removed or weakened.
- [ ] No technical-debt budget is increased.
