---
title: "[TEST-AUDIT-016] Coverage tail burn-down for replay-sensitive modules"
labels: technical-debt, coverage, P0
assignees: []
github_issue: 5928
---

## Context

The `2026-07-03` test-system audit reports **95.61%** merge-gate coverage (gate
≥85%) but **80 modules below 85%**, including replay- and control-plane-sensitive
surfaces that are already flagged in coverage floor ratchets.

## Problem

Ranked tail modules with architectural risk include:

| Module | Coverage | Risk |
|--------|----------|------|
| `composition/bootstrap/runtime/runtime_basics.py` | 76% | Replay-sensitive bootstrap path |
| `application/services/_observability_workflow_checkpoint_support.py` | 76% | Control-plane / checkpoint |
| `infrastructure/adapters/_health_check_policy.py` | 65% | Adapter health_check contract |
| `composition/maintenance_api.py` | 65% | Composition surface |
| `infrastructure/export/debug_export_adapter.py` | 66% | I/O export path |

Regression in these modules can break determinism, replay, or checkpoint semantics
without failing high-level e2e smoke tests.

## Evidence

- `reports/quality/module-coverage-inventory.json`
- `configs/quality/module_coverage_gates.yaml`
- `configs/quality/test_telemetry_baseline.yaml` (coverage gate 95.61%)
- `configs/quality/replay_sensitive_coverage_floors.yaml` (if present)
- `tests/architecture/test_replay_sensitive_coverage_floors.py` (TDX-AUDIT-015 ratchet)

## Acceptance Criteria

- [ ] Top 15 ranked tail targets from `module_coverage_gates.yaml` receive focused unit or integration coverage addenda.
- [ ] `runtime_basics` and checkpoint-support modules meet or exceed their replay-sensitive coverage floors.
- [ ] `module-coverage-inventory.json` is regenerated via canonical refresh script.
- [ ] Coverage-verify lane remains green without lowering global or per-module gates.
- [ ] No technical-debt budget is increased.

## Related

- Complements `TDX-AUDIT-015` replay-sensitive coverage floors; this issue tracks **test authoring** for the tail, not ratchet wiring alone.
