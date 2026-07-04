---
title: "[TDX-AUDIT-006] Reopen hotspot tail coverage ratchet for replay-sensitive runtime seams"
labels: P1, technical-debt, coverage, determinism, observability, control-plane
assignees: []
---

## Context

Current `main` has `0` uncovered and `0` unmeasured modules, but the
`2026-07-01` audit still found `855` partially covered modules and a repo-wide
branch coverage tail at `82.99%`. The most relevant residual tails remain in
control-plane and runtime/observability seams.

The earlier hotspot coverage follow-up `#5575` is closed, so the remaining tail
work needs a new owner.

## Evidence

- `reports/quality/module-coverage-inventory.json`
- `reports/quality/hotspot-coverage-tail-owner-map.json`
- `reports/quality/coverage-tail-branch-gate-plan.md`
- `src/bioetl/application/services/control_plane/workflow/execution_preparation_incremental.py`
- `src/bioetl/composition/bootstrap/runtime/runtime_basics.py`
- `src/bioetl/infrastructure/observability/tracing.py`

## Problem

This is test debt and determinism-risk debt.

The repo is green on uncovered-module governance, but replay-sensitive and
branch-heavy seams still rely on partial coverage and owner-tail bookkeeping
instead of stronger behavioral evidence.

## Required Outcome

- Add targeted behavioral tests for the lowest-value tails in replay-sensitive
  modules.
- Raise the live hotspot tail floor instead of only preserving `0` uncovered
  modules.
- Prepare the branch-tail evidence needed for a future stricter gate.

## File-level Implementation Plan

### Changes

- `reports/quality/hotspot-coverage-tail-owner-map.json`: refresh owner-tail
  evidence after each new test batch.
- `src/bioetl/application/services/control_plane/workflow/execution_preparation_incremental.py`:
  cover branch-heavy preparation paths.
- `src/bioetl/composition/bootstrap/runtime/runtime_basics.py`: strengthen
  runtime setup behavior coverage.
- `src/bioetl/infrastructure/observability/tracing.py`: add branch and failure
  path coverage without assertless smoke tests.

### Refactoring actions

Prefer deterministic behavioral tests and focused golden/regression coverage
over import-only or assertless coverage padding.

## Constraints

- Do not fabricate coverage XML or lower existing coverage governance.
- Do not satisfy the issue with smoke-only tests.
- Do not increase debt budgets or relax branch-tail plans.

## Acceptance Criteria

- [ ] At least one hotspot tail module measurably increases coverage on the
      canonical inventory.
- [ ] Replay-sensitive or branch-heavy paths gain focused behavioral tests.
- [ ] Coverage inventory hash and architecture checks pass after refresh.
- [ ] Branch-tail evidence improves without lowering aggregate coverage.

