---
title: "[TDX-AUDIT-015] Ratchet replay-sensitive partial-coverage module floors beyond zero uncovered"
labels: P0, technical-debt, coverage, determinism, control-plane, replay
assignees: []
---

## Context

Governance is green on uncovered modules (`0` uncovered, `0` unmeasured), but
the `2026-07-03` audit still reports `855` partially covered modules across
`2211` source modules. Replay-sensitive tails remain in control-plane workflow,
bootstrap runtime setup, and infrastructure observability adapters.

Wave 2 added DQ golden/property tests and ledger invariant tests (`#5861`,
`#5862`), and Wave 1 `#5844` tracked hotspot tail coverage, but there is still
no fail-fast floor for named replay-sensitive modules beyond aggregate zero
uncovered.

## Evidence

- `reports/quality/module-coverage-inventory.json`
- `reports/quality/hotspot-coverage-tail-owner-map.json`
- `reports/quality/coverage-tail-branch-gate-plan.md`
- `configs/quality/module_coverage_gates.yaml`
- `src/bioetl/application/services/control_plane/workflow/execution_preparation_incremental.py`
- `src/bioetl/composition/bootstrap/runtime/runtime_basics.py`
- `src/bioetl/infrastructure/observability/tracing.py`
- `tests/unit/domain/control_plane/test_ledger_core_events_replay.py`
- `tests/unit/domain/behavior/test_dq_rule_evaluator_golden.py`

## Problem

This is test debt and determinism-risk debt.

The repo can stay green while replay-sensitive branches remain only partially
covered. That is especially risky for control-plane ledger/replay, checkpoint,
and DQ evaluation seams.

## Required Outcome

- Define a reviewed allowlist of replay-sensitive modules with minimum covered
  line-percent or branch-evidence floors.
- Add focused behavioral/golden/replay tests for the lowest-evidence modules in
  that allowlist.
- Refresh module-coverage inventory and hotspot tail owner map after each batch.

## File-level Implementation Plan

### Changes

- `configs/quality/module_coverage_gates.yaml`: add replay-sensitive module
  floor ratchets (flat or increasing coverage only).
- `tests/architecture/test_replay_sensitive_coverage_floor_ratchet.py`: new
  guard comparing inventory to committed floors.
- `reports/quality/hotspot-coverage-tail-owner-map.json`: refresh owner evidence.
- Target modules (initial batch):
  - `src/bioetl/application/services/control_plane/workflow/execution_preparation_incremental.py`
  - `src/bioetl/composition/bootstrap/runtime/runtime_basics.py`
  - `src/bioetl/infrastructure/observability/tracing.py`

### Refactoring actions

Prefer deterministic behavioral tests over import-only coverage padding. Reuse
golden fixtures where replay ordering matters.

## Constraints

- Do not fabricate coverage XML or lower existing aggregate gates.
- Do not satisfy the issue with assertless smoke-only tests.
- Do not increase debt budgets.

## Acceptance Criteria

- [ ] Replay-sensitive module allowlist and floors are committed in config.
- [ ] Architecture CI fails when any allowlisted module drops below its floor.
- [ ] At least three named replay-sensitive modules gain focused behavioral
      tests in this wave.
- [ ] `module-coverage-inventory.json` hash refresh passes architecture checks.
