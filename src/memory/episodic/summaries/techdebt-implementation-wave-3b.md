---
id: techdebt-implementation-wave-3b
title: Observability known-gap text cleanup
task_id: techdebt-implementation-wave-3b
created_at: '2026-05-13T15:29:54Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-control-plane-v1.json
summary: 'Finished the active observability inventory cleanup by removing literal
  future metric names from the shipped control-plane dashboard text while preserving
  the known-gap operator guidance. Validation: bash scripts/engineering/dev/run_pytest.sh
  --skip-preflight tests/integration/test_grafana_config.py -k control_plane_missing_signals_text_panel_exists
  or control_plane_no_missing_metric_promql; repo inventory snapshot now reports documented_without_registry=[]
  and violations={}. Debt outcome for touched surfaces: improved.'
---

# Episodic summary

## Task

- Title: Observability known-gap text cleanup

## Outcome

- Finished the active observability inventory cleanup by removing literal future metric names from the shipped control-plane dashboard text while preserving the known-gap operator guidance. Validation: bash scripts/engineering/dev/run_pytest.sh --skip-preflight tests/integration/test_grafana_config.py -k control_plane_missing_signals_text_panel_exists or control_plane_no_missing_metric_promql; repo inventory snapshot now reports documented_without_registry=[] and violations={}. Debt outcome for touched surfaces: improved.

## Lessons learned

- Replace with durable follow-up if needed
