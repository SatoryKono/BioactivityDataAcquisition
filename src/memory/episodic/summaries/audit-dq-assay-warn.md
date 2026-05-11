---
id: audit-dq-assay-warn
title: Investigate assay DQ WARN status
task_id: audit-dq-assay-warn
created_at: '2026-05-11T13:12:58Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/prometheus-rules/bioetl_observability.yml
summary: Confirmed Monitor DQ Current Status is WARN for chembl_assay because bioetl_dq_current_reason
  publishes dq_monitor_disabled from bioetl_dq_monitor_enabled=0.
---

# Episodic summary

## Task

- Title: Investigate assay DQ WARN status

## Outcome

- Confirmed Monitor DQ Current Status is WARN for chembl_assay because bioetl_dq_current_reason publishes dq_monitor_disabled from bioetl_dq_monitor_enabled=0.

## Lessons learned

- Replace with durable follow-up if needed
