---
title: "[TEST-AUDIT-015] Expand integration determinism matrix beyond single gate"
labels: test, determinism, P1
assignees: []
---

## Context

The `2026-07-03` test-system audit rated determinism governance as strong at the
architecture layer (`uuid4` and `date.today` call sites = 0 in tests), but thin at
the integration lane for replay/idempotency proof across entities and providers.

## Problem

`tests/integration/determinism/` currently exposes a single primary gate:

- `tests/integration/determinism/test_reproducibility_determinism_gate.py`

Idempotency coverage is similarly sparse (one tracked file). The canonical test
matrix declares broader replay/determinism expectations per provider and entity,
but the integration matrix does not yet exercise enough combinations to match that
policy surface.

## Evidence

- `tests/integration/determinism/test_reproducibility_determinism_gate.py`
- `configs/quality/test_matrix.yaml` (entity/provider ownership rows)
- `configs/quality/integration_vcr_policy.yaml`
- `reports/quality/test-governance-current.json`
- `tests/helpers/control_plane_replay.py` (if present — extend as shared builder)

## Acceptance Criteria

- [ ] Integration determinism lane covers at least ChEMBL and composite replay scenarios with tracked fixtures.
- [ ] Idempotency semantics are asserted for at least one additional entity/provider combination beyond the current gate.
- [ ] New tests use VCR replay-by-default (`VCR_RECORD_MODE=none`) and fixed clocks (`FIXED_TEST_TIME` / `tests/helpers/clock.py`).
- [ ] `test_matrix.yaml` documents the expanded tracked fixture matrix.
- [ ] No live-network dependency is introduced.
- [ ] No technical-debt budget is increased.

## Related

- Aligns with replay-sensitive coverage work in `TDX-AUDIT-015` (coverage floors), but this issue targets **integration proof**, not unit coverage alone.
