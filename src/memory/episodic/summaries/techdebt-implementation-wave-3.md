---
id: techdebt-implementation-wave-3
title: Observability inventory drift cleanup
task_id: techdebt-implementation-wave-3
created_at: '2026-05-13T15:26:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/report_observability_metric_inventory.py
summary: 'Reduced observability inventory debt by fixing report-observability-metric-inventory
  false negatives for direct Prometheus collectors and keyword-only MetricsPort calls,
  adding explicit recording-rule metric declarations for shipped current-status/L0
  operator metrics, shrinking the allowlist to real known gaps, and updating observability
  governance/docs. Validation: bash scripts/engineering/dev/run_pytest.sh --skip-preflight
  tests/unit/scripts/test_report_observability_metric_inventory.py tests/architecture/test_observability_metric_governance.py;
  repo inventory snapshot now reports dead_metrics=[], registered_without_runtime=[],
  rules_without_registry=[], documented_without_registry=[bioetl_checkpoint_age_seconds,
  bioetl_replay_duplicate_records_total], violations={}. Debt outcome for touched
  surfaces: improved.'
---

# Episodic summary

## Task

- Title: Observability inventory drift cleanup

## Outcome

- Reduced observability inventory debt by fixing report-observability-metric-inventory false negatives for direct Prometheus collectors and keyword-only MetricsPort calls, adding explicit recording-rule metric declarations for shipped current-status/L0 operator metrics, shrinking the allowlist to real known gaps, and updating observability governance/docs. Validation: bash scripts/engineering/dev/run_pytest.sh --skip-preflight tests/unit/scripts/test_report_observability_metric_inventory.py tests/architecture/test_observability_metric_governance.py; repo inventory snapshot now reports dead_metrics=[], registered_without_runtime=[], rules_without_registry=[], documented_without_registry=[bioetl_checkpoint_age_seconds, bioetl_replay_duplicate_records_total], violations={}. Debt outcome for touched surfaces: improved.

## Lessons learned

- Replace with durable follow-up if needed
