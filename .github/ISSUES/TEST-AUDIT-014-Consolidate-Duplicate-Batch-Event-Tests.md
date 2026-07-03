---
title: "[TEST-AUDIT-014] Consolidate duplicate Batch event unit tests"
labels: technical-debt, test, P1
assignees: []
github_issue: 5926
---

## Context

The `2026-07-03` test-system audit found minimal duplicate test-name inventory
overall (2 groups / 4 occurrences), but one meaningful overlap exists in Batch
aggregate unit coverage.

## Problem

The same behavioral scenarios are asserted under identical test function names in
two files:

- `tests/unit/domain/aggregates/test_batch_fsm_exhaustive.py`
  - `test_mark_committed_emits_batch_written_event`
  - `test_mark_failed_emits_batch_failed_event`
- `tests/unit/domain/aggregates/test_batch_internal_modules.py`
  - `test_mark_committed_emits_batch_written_event`
  - `test_mark_failed_emits_batch_failed_event`

This creates confusing failure attribution, wastes runtime, and violates the
duplicate-name budget signal in `test-duplicate-name-inventory.json`.

## Evidence

- `reports/quality/test-duplicate-name-inventory.json`
- `reports/quality/test-governance-current.json`
- `tests/unit/domain/aggregates/test_batch_fsm_exhaustive.py`
- `tests/unit/domain/aggregates/test_batch_internal_modules.py`

## Acceptance Criteria

- [ ] Duplicate Batch event test names are consolidated into a single canonical owner file.
- [ ] FSM exhaustiveness coverage for OPEN→SEALED→WRITING→COMMITTED/FAILED is preserved.
- [ ] `test-duplicate-name-inventory.json` no longer reports these cross-file duplicates.
- [ ] No reduction in Batch FSM transition or event-emission assertions.
- [ ] No technical-debt budget is increased.

## Implementation Notes

Prefer extracting shared event assertions into a small helper or mixin used by
the exhaustive FSM module, rather than deleting behavioral coverage from
`test_batch_internal_modules.py` without replacement.
