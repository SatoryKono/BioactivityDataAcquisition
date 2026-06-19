---
id: close-observability-governance-5437-2026-06-19
title: Close observability governance issue 5437
task_id: close-observability-governance-5437-2026-06-19
created_at: '2026-06-19T16:18:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Closed observability governance issue #5437 by moving endpoint/table risky-label
  metric families into declared_label_contract_metrics, shrinking declared_risky_label_review_required
  allowlist from 13 to 2 while keeping runtime_cardinality_review_required at 0 and
  declared_risky_label_review_required at 0 in regenerated reports/observability/runtime_cardinality_inventory.json.
  Validated report_observability_metric_inventory --check, local cardinality fallback
  review, diff check, and targeted observability pytest set.'
---

# Episodic summary

## Task

- Title: Close observability governance issue 5437

## Outcome

- Closed observability governance issue #5437 by moving endpoint/table risky-label metric families into declared_label_contract_metrics, shrinking declared_risky_label_review_required allowlist from 13 to 2 while keeping runtime_cardinality_review_required at 0 and declared_risky_label_review_required at 0 in regenerated reports/observability/runtime_cardinality_inventory.json. Validated report_observability_metric_inventory --check, local cardinality fallback review, diff check, and targeted observability pytest set.

## Lessons learned

- Replace with durable follow-up if needed
