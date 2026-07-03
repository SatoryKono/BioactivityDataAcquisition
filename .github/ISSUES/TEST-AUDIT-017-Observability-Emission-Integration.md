---
title: "[TEST-AUDIT-017] Observability emission integration for composite and checkpoint paths"
labels: test, observability, P1
assignees: []
github_issue: 5929
---

## Context

The `2026-07-03` test-system audit found strong observability **governance**
coverage (metric naming, dashboard contracts, doc drift guards) but a thin
**runtime emission** lane compared to architecture surface area.

## Problem

Observability testing is skewed toward docs/governance architecture tests (~9+
files) versus runtime port behavior:

- Key integration file: `tests/integration/test_observability_emission_integration.py` (single primary emission test)
- Duplicate unit paths: `test_runner_observability_mixin.py` under `runner_pkg/` and `composite/`

Composite replay and checkpoint spans are under-tested relative to declared
MetricsPort/TracingPort contracts (`test_governance_audit.yaml` references issue
`#4174` for emission gap tracking).

## Evidence

- `tests/integration/test_observability_emission_integration.py`
- `tests/unit/application/runner_pkg/test_runner_observability_mixin.py`
- `tests/unit/application/composite/test_runner_observability_mixin.py`
- `tests/architecture/test_observability_metric_governance.py`
- `tests/architecture/test_observability_dashboard_contracts.py`
- `configs/quality/test_governance_audit.yaml`

## Acceptance Criteria

- [ ] Integration tests assert metric/span emission for composite pipeline replay and checkpoint workflow paths.
- [ ] Tests use fakes or in-memory observability ports — no live telemetry backend.
- [ ] Duplicate observability mixin unit paths are consolidated or one path is explicitly deprecated with coverage preserved.
- [ ] Architecture governance tests for metric naming remain unchanged and green.
- [ ] No technical-debt budget is increased.
