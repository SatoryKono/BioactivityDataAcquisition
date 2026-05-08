---
id: chembl-target-control-plane-fix
title: Fix chembl_target control-plane overview summary
task_id: chembl-target-control-plane-fix
created_at: '2026-05-08T19:14:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/prometheus-rules/bioetl_observability.yml
summary: Fixed overview control-plane summary to coalesce absent alert-condition series
  to explicit zero so clean control-plane runs no longer fail-close to UNKNOWN; verified
  with targeted Prometheus rule tests and live chembl_target metrics.
---

# Episodic summary

## Task

- Title: Fix chembl_target control-plane overview summary

## Outcome

- Fixed overview control-plane summary to coalesce absent alert-condition series to explicit zero so clean control-plane runs no longer fail-close to UNKNOWN; verified with targeted Prometheus rule tests and live chembl_target metrics.

## Lessons learned

- Replace with durable follow-up if needed
