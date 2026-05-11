---
id: chembl-target-dq-crit-debug
title: Investigate chembl_target DQ CRIT with zero filtered records
task_id: chembl-target-dq-crit-debug
created_at: '2026-05-11T14:29:23Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/prometheus-rules/bioetl_observability.yml
summary: Confirmed that chembl_target is CRIT because bioetl_dq_current_reason emits
  silver_validation_failure as a crit current reason from bioetl_silver_validation_failures_total
  over 30m, while filtered_out remains empty and quarantined records are non-zero.
---

# Episodic summary

## Task

- Title: Investigate chembl_target DQ CRIT with zero filtered records

## Outcome

- Confirmed that chembl_target is CRIT because bioetl_dq_current_reason emits silver_validation_failure as a crit current reason from bioetl_silver_validation_failures_total over 30m, while filtered_out remains empty and quarantined records are non-zero.

## Lessons learned

- Replace with durable follow-up if needed
