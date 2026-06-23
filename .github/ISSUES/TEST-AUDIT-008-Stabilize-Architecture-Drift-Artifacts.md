---
title: "[TEST-AUDIT-008] Stabilize architecture drift artifacts that break reproducible test baselines"
github_issue: 5491
labels: ci, technical-debt
assignees: []
---

## Context

The 2026-06-22 test-system audit found that the strongest current correctness
risk is drift-sensitive architecture artifacts that fail when generated
inventories, hashes, retention windows, or time-seam allowlists are out of sync.

## Problem

Recent failures include:

- `tests/architecture/test_time_seam_classification.py::test_all_direct_wall_clock_calls_are_classified`
- `tests/architecture/test_replay_safe_cleanup_inventory.py::test_reports_quality_ttl_artifacts_are_not_past_retention_window`
- `tests/architecture/test_tech_debt_issues_5387_5394_closeout.py::test_issue_5387_scorecard_coverage_evidence_matches_inventory`

These failures are P0 because they affect deterministic CI signal and
replay-safe quality gates, even when domain/application behavior has not
regressed.

## Evidence

- `tests/architecture/test_time_seam_classification.py`
- `tests/architecture/test_replay_safe_cleanup_inventory.py`
- `tests/architecture/test_tech_debt_issues_5387_5394_closeout.py`
- `reports/quality/architecture-quality-scorecard.json`
- `reports/quality/module-coverage-inventory.json`
- `reports/quality/test-runs/rollup.md`

## Acceptance Criteria

- [ ] The three named architecture failures pass on a clean checkout after canonical refresh.
- [ ] Stale quality TTL artifacts are either removed by policy or excluded through a documented retention rule.
- [ ] Scorecard/hash evidence is regenerated through the canonical script and matches the live collector.
- [ ] The fix preserves deterministic/replay-safe wall-clock policy.
- [ ] No technical-debt budgets are increased.

