---
title: "[TEST-AUDIT-013] Persist architecture governance scan cache in CI"
labels: ci, technical-debt, P0
assignees: []
---

## Context

The `2026-07-03` test-system audit on `main` @ `84a42c127` found that cold-run
latency is still dominated by architecture governance scanners in shard S7, even
after lane isolation (`architecture-fast-boundary` vs `architecture-slow-governance`).

A local probe already documents in-process cache effectiveness, but CI does not
yet persist a warm cache artifact keyed to `source_tree_sha256`.

## Problem

Slow-test telemetry shows governance scanners at the top of the cold-run profile:

- `tests.architecture.test_checkpoint_compatibility_runtime_facade_usage::test_checkpoint_compatibility_runtime_facade_is_not_used_in_tests` — **42.8s**
- `tests.architecture.test_checkpoint_compatibility_runtime_facade_usage::test_checkpoint_compatibility_runtime_facade_is_not_used_in_src` — **28.1s**
- `tests.architecture.test_config_discrepancy_baseline::test_config_discrepancy_baseline_matches_live_generator` — **24.0s**
- `tests.architecture.test_config_discrepancy_report::test_config_discrepancy_report_matches_deterministic_generator` — **23.0s**

The `slow_governance_cache_probe` in `test_telemetry_baseline.yaml` records
`collect_test_governance_report` improving from **28.676s → 0.001s** on repeat
(in-process cache), and subprocess reuse via `tests.architecture.conftest.cached_subprocess_run`.
That benefit is not yet durable across CI jobs.

## Evidence

- `configs/quality/test_telemetry_baseline.yaml` (`slow_governance_cache_probe`, top slow tests)
- `reports/test-telemetry/slowest-tests.md`
- `tests/architecture/conftest.py` (`cached_subprocess_run`, `_run_cached_subprocess`)
- `configs/quality/test_matrix.yaml` (`architecture-slow-governance` lane)
- `reports/quality/test-governance-current.json`

## Acceptance Criteria

- [ ] CI warm job persists architecture governance scan cache keyed to `source_tree_sha256`.
- [ ] PR lanes restore cache before `architecture-slow-governance` and invalidate on hash drift.
- [ ] Cold-run top scanners show measurable reduction in `reports/test-telemetry/slowest-tests.md` after rollout.
- [ ] Fast boundary lane remains free of repo-wide scanner subprocesses.
- [ ] No architecture invariant is removed or weakened.
- [ ] No technical-debt budget is increased.

## Related

- Continues `TEST-AUDIT-009` ([#5493](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5493))
- Issue probe anchor: `#4663` (`slow_governance_cache_probe.issue_ref`)
